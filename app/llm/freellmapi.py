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
        """Perform comprehensive step-by-step LLM endpoint health check per specifications."""
        start_time = time.time()
        res_data = {
            "provider": "FreeLLMAPI",
            "base_url": self.base_url,
            "model": self.model,
            "server_reachable": "NO",
            "models_endpoint": "NO",
            "chat_endpoint": "NO",
            "authentication": "FAILED",
            "simple_completion": "FAILED",
            "structured_json": "FAILED",
            "latency": 0.0,
            "available_models": [],
            "error": None
        }

        # 1. Check server reachability (GET base host)
        root_url = self.base_url.rsplit("/v1", 1)[0] or self.base_url
        target_root = root_url if root_url.startswith("http") else f"http://{root_url}"
        try:
            r_root = requests.get(target_root, timeout=3)
            res_data["server_reachable"] = f"YES (HTTP {r_root.status_code})"
        except Exception as e:
            res_data["server_reachable"] = "NO"
            res_data["error"] = f"Connection refused at {target_root} ({e})"

        # 2. Check /v1/models endpoint
        models_url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            r_models = requests.get(models_url, headers=headers, timeout=4)
            if r_models.status_code == 200:
                res_data["models_endpoint"] = "YES (200 OK)"
                try:
                    m_json = r_models.json()
                    model_list = [m.get("id") for m in m_json.get("data", []) if isinstance(m, dict)]
                    res_data["available_models"] = model_list
                except Exception:
                    res_data["available_models"] = []
            else:
                res_data["models_endpoint"] = f"FAILED (HTTP {r_models.status_code})"
        except Exception as e:
            res_data["models_endpoint"] = f"FAILED ({e})"

        # 3. Check Chat endpoint / simple completion & authentication (STEP 5 test prompt)
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
                timeout=6
            )
            latency = round(time.time() - start_time, 2)
            res_data["latency"] = latency

            if r_chat.status_code == 200:
                res_data["chat_endpoint"] = "YES (200 OK)"
                res_data["authentication"] = "OK"
                res_data["simple_completion"] = "OK"

                # Test structured JSON parsing
                content = r_chat.json()["choices"][0]["message"]["content"]
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and parsed.get("test") is True:
                        res_data["structured_json"] = "OK"
                    else:
                        res_data["structured_json"] = "FAILED (JSON key mismatch)"
                except Exception:
                    res_data["structured_json"] = "FAILED (JSON syntax error)"

            elif r_chat.status_code in [401, 403]:
                res_data["chat_endpoint"] = f"FAILED (HTTP {r_chat.status_code})"
                res_data["authentication"] = "FAILED (Invalid API key)"
                res_data["error"] = f"Authentication error HTTP {r_chat.status_code}: {r_chat.text[:150]}"
            else:
                res_data["chat_endpoint"] = f"FAILED (HTTP {r_chat.status_code})"
                res_data["error"] = f"HTTP {r_chat.status_code}: {r_chat.text[:150]}"

        except Exception as e:
            res_data["latency"] = round(time.time() - start_time, 2)
            res_data["chat_endpoint"] = f"FAILED ({e})"
            if not res_data["error"]:
                res_data["error"] = str(e)

        return res_data

    def get_formatted_health_report(self) -> str:
        h = self.health_check()
        lines = [
            "============================================================",
            "LLM HEALTH CHECK",
            "============================================================",
            f"Provider           : {h['provider']}",
            f"Base URL           : {h['base_url']}",
            f"Model              : {h['model']}",
            "",
            f"Server reachable   : {h['server_reachable']}",
            f"Models endpoint    : {h['models_endpoint']}",
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

        if h["server_reachable"] == "NO":
            lines.extend([
                "",
                "RECOMMENDED .ENV DIAGNOSTIC:",
                "------------------------------------------------------------",
                f"1. No local LLM service is running on {h['base_url']}",
                "2. Please start your local FreeLLMAPI / Ollama / LM Studio server.",
                "3. Ensure your server exposes an OpenAI-compatible API.",
                "4. Update .env variables once your local server is running:",
                "   LLM_PROVIDER=freellmapi",
                "   LLM_BASE_URL=http://localhost:<YOUR_PORT>/v1",
                "   LLM_API_KEY=<YOUR_KEY>",
                "   LLM_MODEL=<AVAILABLE_MODEL_ID>"
            ])
        lines.append("============================================================")
        return "\n".join(lines)

