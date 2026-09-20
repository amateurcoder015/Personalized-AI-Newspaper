import json
import logging
import re
import time
from typing import Dict, Any, Optional
import requests
from app.llm.base import LLMProvider
from app.llm.cache import LLMCache

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """LLM Provider targeting Google Gemini via OpenAI-compatible endpoint.
    Base URL: https://generativelanguage.googleapis.com/v1beta/openai
    Default Model: gemini-1.5-flash
    """

    def __init__(
        self,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        api_key: str = "",
        model: str = "gemini-1.5-flash",
        cache: Optional[LLMCache] = None
    ):
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        self.api_key = api_key
        self.model = model or "gemini-1.5-flash"
        self.cache = cache
        self.last_error: Optional[str] = None

    def _call_api(self, messages: list) -> Optional[str]:
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            self.last_error = "Gemini API key is not configured in .env (LLM_API_KEY)"
            logger.warning(self.last_error)
            if self.cache:
                self.cache.record_failure()
            return None

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
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                self.last_error = None
                return data["choices"][0]["message"]["content"]
            else:
                err_msg = f"HTTP status {response.status_code}: {response.text[:200]}"
                self.last_error = err_msg
                logger.warning(f"Gemini API returned {err_msg}")
                if self.cache:
                    self.cache.record_failure()
                return None
        except Exception as e:
            err_msg = f"Could not connect to Gemini API ({self.base_url}): {e}"
            self.last_error = err_msg
            logger.warning(err_msg)
            if self.cache:
                self.cache.record_failure()
            return None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
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
            logger.warning(f"Failed to parse Gemini structured JSON output ({e}). Snippet: {raw_res[:150]}")
            if self.cache:
                self.cache.record_fallback()
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive step-by-step Gemini health check."""
        start_time = time.time()
        res_data = {
            "provider": "Gemini (Google AI)",
            "base_url": self.base_url,
            "model": self.model,
            "server_reachable": "NO",
            "models_endpoint": "NO",
            "chat_endpoint": "NO",
            "authentication": "FAILED",
            "simple_completion": "FAILED",
            "structured_json": "FAILED",
            "latency": 0.0,
            "available_models": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
            "error": None
        }

        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            res_data["error"] = "Gemini API key is not set in .env (LLM_API_KEY=...)"
            return res_data

        # 1. Reachability
        try:
            r = requests.get("https://generativelanguage.googleapis.com", timeout=4)
            res_data["server_reachable"] = f"YES (HTTP {r.status_code})"
        except Exception as e:
            res_data["server_reachable"] = f"FAILED ({e})"
            res_data["error"] = f"Cannot reach Google API servers: {e}"
            return res_data

        # 2. Test completion with Step 5 prompt
        completion_prompt = (
            'Return valid JSON with:\n'
            '{\n'
            '  "test": true,\n'
            '  "message": "LLM connection successful"\n'
            '}'
        )
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": completion_prompt}],
            "temperature": 0.2
        }

        try:
            r_chat = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=8
            )
            latency = round(time.time() - start_time, 2)
            res_data["latency"] = latency

            if r_chat.status_code == 200:
                res_data["models_endpoint"] = "YES (200 OK)"
                res_data["chat_endpoint"] = "YES (200 OK)"
                res_data["authentication"] = "OK"
                res_data["simple_completion"] = "OK"

                content = r_chat.json()["choices"][0]["message"]["content"]
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and parsed.get("test") is True:
                        res_data["structured_json"] = "OK"
                    else:
                        res_data["structured_json"] = "FAILED (JSON key mismatch)"
                except Exception:
                    res_data["structured_json"] = "FAILED (JSON syntax error)"

            elif r_chat.status_code in [400, 401, 403]:
                res_data["authentication"] = "FAILED (Invalid Gemini API Key or project quota)"
                res_data["error"] = f"HTTP {r_chat.status_code}: {r_chat.text[:200]}"
            else:
                res_data["error"] = f"HTTP {r_chat.status_code}: {r_chat.text[:200]}"

        except Exception as e:
            res_data["latency"] = round(time.time() - start_time, 2)
            res_data["chat_endpoint"] = f"FAILED ({e})"
            res_data["error"] = str(e)

        return res_data

    def get_formatted_health_report(self) -> str:
        h = self.health_check()
        lines = [
            "============================================================",
            "LLM HEALTH CHECK — GEMINI (GOOGLE AI)",
            "============================================================",
            f"Provider           : {h['provider']}",
            f"Base URL           : {h['base_url']}",
            f"Model              : {h['model']}",
            "",
            f"Server reachable   : {h['server_reachable']}",
            f"Chat endpoint      : {h['chat_endpoint']}",
            f"Authentication     : {h['authentication']}",
            f"Simple completion  : {h['simple_completion']}",
            f"Structured JSON    : {h['structured_json']}",
            f"Latency            : {h['latency']}s",
        ]
        if h["available_models"]:
            lines.append(f"Available models   : {', '.join(h['available_models'])}")
        if h["error"]:
            lines.append(f"Error details      : {h['error']}")
        if h["authentication"] != "OK":
            lines.extend([
                "",
                "ACTION REQUIRED IN .ENV:",
                "------------------------------------------------------------",
                "Please edit .env and set your Google AI Studio Gemini API key:",
                "   LLM_PROVIDER=gemini",
                "   LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai",
                "   LLM_API_KEY=YOUR_ACTUAL_GEMINI_API_KEY",
                "   LLM_MODEL=gemini-1.5-flash"
            ])
        lines.append("============================================================")
        return "\n".join(lines)
