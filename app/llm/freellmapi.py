import json
import logging
import re
from typing import Dict, Any, Optional
import requests
from app.llm.base import LLMProvider
from app.llm.cache import LLMCache

logger = logging.getLogger(__name__)


class FreeLLMAPIProvider(LLMProvider):
    """LLM Provider targeting FreeLLMAPI or OpenAI-compatible endpoint.
    Includes SQLite prompt caching and token accounting.
    """

    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: str = "free_key", model: str = "gpt-3.5-turbo", cache: Optional[LLMCache] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "free_key"
        self.model = model
        self.cache = cache

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
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"FreeLLMAPI returned HTTP status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.warning(f"Could not connect to LLM API ({self.base_url}): {e}. Using heuristic fallback.")
            return None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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
        if not res:
            res = self._heuristic_fallback(prompt)

        # 2. Record usage & save to cache
        if self.cache:
            self.cache.record_usage(prompt, res)
            self.cache.put(prompt, self.model, res)

        return res

    def generate_structured(self, prompt: str, schema: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        instructed_prompt = f"{prompt}\n\nIMPORTANT: Respond with ONLY valid raw JSON matching standard schema keys."
        raw_res = self.generate(instructed_prompt, system_prompt=system_prompt)

        try:
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_res, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match_obj = re.search(r"(\{.*\})", raw_res, re.DOTALL)
                json_str = json_match_obj.group(1) if json_match_obj else raw_res

            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse LLM structured JSON output ({e}). Output snippet: {raw_res[:150]}")
            return self._heuristic_structured_fallback(prompt)

    def _heuristic_fallback(self, prompt: str) -> str:
        return "Key market developments unfolded today as economic indicators and corporate actions aligned across major sectors."

    def _heuristic_structured_fallback(self, prompt: str) -> Dict[str, Any]:
        title_match = re.search(r"Title:\s*(.+)", prompt)
        title = title_match.group(1).strip() if title_match else "Market Update"

        content_match = re.search(r"Content/Snippet:\s*(.+?)(?=\n\nReturn JSON|\n\nIMPORTANT|$)", prompt, re.DOTALL)
        snippet = content_match.group(1).strip() if content_match else ""
        snippet = re.sub(r"\s+", " ", snippet)[:300]

        summary = snippet if snippet else f"Key developments regarding {title} reported today across financial markets and technology sectors."
        return {
            "headline": title,
            "summary": summary,
            "why_it_matters": f"Key implications for markets, economic trends, and corporate operations related to {title[:50]}.",
            "category": "india",
            "gold_driver": "Gold prices held steady as market participants weighed global rate expectations and central bank reserves.",
            "silver_driver": "Silver tracked precious metal market movements alongside industrial demand indicators.",
            "connections": [
                {
                    "title": "Yield Movements and Commodity Valuations",
                    "premise": "Shifting interest rate expectations influenced bond yields and foreign exchange rates.",
                    "chain_steps": ["Central Bank Rate Signals", "Bond Yield Adjustments", "Currency Valuation Shifts", "Impact on Commodity Prices"],
                    "why_matters": "Demonstrates how monetary policy stance propagates through credit markets into commodity and equity valuations."
                }
            ],
            "topics": ["Markets", "Business"],
            "entities": []
        }
