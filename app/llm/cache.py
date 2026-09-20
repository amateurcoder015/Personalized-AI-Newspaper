import hashlib
import logging
from typing import Optional, Dict, Any
from app.database import DatabaseManager
from app.database.models import LLMUsageLog

logger = logging.getLogger(__name__)


class LLMCache:
    """Manages prompt hashing, SQLite caching, and token usage accounting."""

    def __init__(self, db: DatabaseManager, enabled: bool = True):
        self.db = db
        self.enabled = enabled
        self.calls = 0
        self.successful = 0
        self.failed = 0
        self.fallback = 0
        self.cache_hits = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def compute_hash(self, prompt: str, model: str) -> str:
        raw = f"{model}::{prompt}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, prompt: str, model: str) -> Optional[str]:
        if not self.enabled:
            return None
        prompt_hash = self.compute_hash(prompt, model)
        cached_response = self.db.get_cached_llm_response(prompt_hash)
        if cached_response:
            self.calls += 1
            self.cache_hits += 1
            logger.info(f"LLM Cache HIT for prompt hash {prompt_hash[:8]}")
            return cached_response
        return None

    def put(self, prompt: str, model: str, response: str) -> None:
        if not self.enabled:
            return
        prompt_hash = self.compute_hash(prompt, model)
        self.db.save_llm_cache(prompt_hash, prompt, response, model)

    def record_success(self, prompt_text: str, response_text: str) -> None:
        self.calls += 1
        self.successful += 1
        in_tok = max(1, len(prompt_text) // 4)
        out_tok = max(1, len(response_text) // 4)
        self.input_tokens += in_tok
        self.output_tokens += out_tok

    def record_failure(self) -> None:
        self.calls += 1
        self.failed += 1

    def record_fallback(self) -> None:
        self.fallback += 1

    def get_summary(self) -> Dict[str, Any]:
        estimated_cost = round(((self.input_tokens / 1000.0) * 0.0015) + ((self.output_tokens / 1000.0) * 0.002), 4)

        log_entry = LLMUsageLog(
            calls=self.calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_hits=self.cache_hits,
            estimated_cost=estimated_cost
        )
        self.db.log_llm_usage(log_entry)

        return {
            "calls": self.calls,
            "successful": self.successful,
            "failed": self.failed,
            "fallback": self.fallback,
            "cache_hits": self.cache_hits,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": f"${estimated_cost:.4f} (estimated)",
            "is_estimated": True
        }

