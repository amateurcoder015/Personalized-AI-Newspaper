import json
import logging
import re
import time
from typing import Dict, Any, Optional, List
import requests
from app.llm.base import LLMProvider
from app.llm.cache import LLMCache

logger = logging.getLogger(__name__)


class FreeLLMAPIProvider(LLMProvider):
    """LLM Provider targeting FreeLLMAPI or OpenAI-compatible endpoint.
    Includes SQLite prompt caching, explicit health check, and token accounting.
    """

    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: str = "free_key", model: str = "gpt-3.5-turbo", cache: Optional[LLMCache] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "free_key"
        self.model = model
        self.cache = cache
        self.last_error: Optional[str] = None

    def _call_api(self, messages: list) -> Optional[str]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                data = response.json()
                self.last_error = None
                return data["choices"][0]["message"]["content"]
            else:
                err_msg = f"HTTP status {response.status_code}: {response.text[:200]}"
                self.last_error = err_msg
                logger.warning(f"FreeLLMAPI returned {err_msg}")
                if self.cache:
                    self.cache.record_failure()
                return None
        except Exception as e:
            err_msg = f"Could not connect to LLM API ({self.base_url}): {e}"
            self.last_error = err_msg
            logger.warning(err_msg)
            if self.cache:
                self.cache.record_failure()
            return None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        # 1. Check SQLite Cache
        if self.cache:
            cached = self.cache.get(prompt, self.model)
            if cached:
                return cached

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        res = self._call_api(messages)
        if res is not None:
            if self.cache:
                self.cache.record_success(prompt, res)
                self.cache.put(prompt, self.model, res)
            return res
        else:
            if self.cache:
                self.cache.record_fallback()
            return None

    def generate_structured(self, prompt: str, schema: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        instructed_prompt = f"{prompt}\n\nIMPORTANT: Respond with ONLY valid raw JSON matching standard schema keys."
        raw_res = self.generate(instructed_prompt, system_prompt=system_prompt)

        if not raw_res:
            return {}

        try:
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_res, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match_obj = re.search(r"(\{.*\})", raw_res, re.DOTALL)
                json_str = json_match_obj.group(1) if json_match_obj else raw_res

            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return parsed
            return {}
        except Exception as e:
            logger.warning(f"Failed to parse LLM structured JSON output ({e}). Snippet: {raw_res[:150]}")
            if self.cache:
                self.cache.record_fallback()
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Perform real LLM health check measuring latency, connectivity, completion, and JSON parsing."""
        start_time = time.time()
        result = {
            "provider": "FreeLLMAPI",
            "endpoint": self.base_url,
            "model": self.model,
            "connection": "FAILED",
            "completion": "FAILED",
            "structured_json": "FAILED",
            "latency": 0.0,
            "error": None
        }

        # Step 1: Connectivity & Basic Completion
        res = self._call_api([{"role": "user", "content": "Say 'LLM_HEALTH_OK'"}])
        latency = round(time.time() - start_time, 2)
        result["latency"] = latency

        if res is not None:
            result["connection"] = "OK"
            result["completion"] = "OK"

            # Step 2: Test Structured JSON
            json_res = self.generate_structured("Return JSON: {\"status\": \"ok\"}")
            if json_res and json_res.get("status") == "ok":
                result["structured_json"] = "OK"
            else:
                result["structured_json"] = "FAILED (JSON parse failure)"
        else:
            result["error"] = self.last_error or "Connection refused / Endpoint unreachable"

        return result

    def get_formatted_health_report(self) -> str:
        h = self.health_check()
        lines = [
            "============================================================",
            "LLM HEALTH CHECK",
            "============================================================",
            f"Provider        : {h['provider']}",
            f"Endpoint        : {h['endpoint']}",
            f"Model           : {h['model']}",
            "",
            f"Connection      : {h['connection']}",
            f"Completion      : {h['completion']}",
            f"Structured JSON : {h['structured_json']}",
            f"Latency         : {h['latency']}s",
        ]
        if h["error"]:
            lines.append(f"Error Details   : {h['error']}")
        lines.append("============================================================")
        return "\n".join(lines)

