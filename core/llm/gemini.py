"""Gemini LLM provider implementation."""

from __future__ import annotations

import json
from typing import Any
import httpx

from core.config import get_settings
from core.logger import get_logger
from core.llm.base import BaseLLMProvider

log = get_logger(__name__)


class GeminiLLMProvider(BaseLLMProvider):
    """
    LLM provider using Google Generative Language API.
    """

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        use_search_grounding: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        settings = get_settings()
        api_key = settings.gemini_api_key

        if not api_key or api_key in ("test-key", "YOUR_GEMINI_API_KEY_HERE", ""):
            log.debug("No valid Gemini API key found; skipping LLM call")
            return None

        model = settings.gemini_model or "gemini-2.0-flash-exp"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": kwargs.get("temperature", 0.2),
            }
        }
        
        if use_search_grounding:
            payload["tools"] = [{"googleSearch": {}}]

        try:
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 25.0)) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # We can't let tenacity catch this unless we raise an exception, but BaseLLMProvider returns None on error.
                # The Discovery Provider wraps this in a tenacity retry, so we should raise for retriable HTTP errors!
                response.raise_for_status()

                res_data = response.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                if isinstance(parsed, (dict, list)):
                    return parsed
                return None
        except httpx.HTTPStatusError as e:
            log.warning("Gemini API returned error status", status_code=e.response.status_code, response=e.response.text)
            raise e
        except Exception as e:
            log.warning("Exception querying Gemini API for structured JSON", error=str(e))
            raise e
