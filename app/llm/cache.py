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
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_hits = 0

    def compute_hash(self, prompt: str, model: str) -> str:
        raw = f"{model}::{prompt}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, prompt: str, model: str) -> Optional[str]:
        if not self.enabled:
            return None
        prompt_hash = self.compute_hash(prompt, model)
        cached_response = self.db.get_cached_llm_response(prompt_hash)
        if cached_response:
            self.cache_hits += 1
            logger.info(f"LLM Cache HIT for prompt hash {prompt_hash[:8]}")
            return cached_response
        return None

    def put(self, prompt: str, model: str, response: str) -> None:
        if not self.enabled:
            return
        prompt_hash = self.compute_hash(prompt, model)
        self.db.save_llm_cache(prompt_hash, prompt, response, model)

    def record_usage(self, prompt_text: str, response_text: str) -> None:
        self.calls += 1
        # Token estimation heuristic (~4 chars = 1 token) if API doesn't report exact tokens
        in_tok = max(1, len(prompt_text) // 4)
        out_tok = max(1, len(response_text) // 4)
        self.input_tokens += in_tok
        self.output_tokens += out_tok

    def get_summary(self) -> Dict[str, Any]:
        # Estimated cost heuristic ($0.0015 / 1k input, $0.002 / 1k output)
        estimated_cost = round(((self.input_tokens / 1000.0) * 0.0015) + ((self.output_tokens / 1000.0) * 0.002), 4)

        # Record to DB log
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
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_hits": self.cache_hits,
            "estimated_cost": f"${estimated_cost:.4f}"
        }
