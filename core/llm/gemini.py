"""Gemini LLM provider implementation."""

from __future__ import annotations

import json
from typing import Any
import httpx

from core.config import get_settings
from core.logger import get_logger
from core.llm.base import BaseLLMProvider

log = get_logger(__name__)


import asyncio
import time

_gemini_semaphore = asyncio.Semaphore(1)
_last_request_time = 0.0
REQUEST_DELAY_SECONDS = 4.0

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

        model = settings.gemini_model or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}
        def flatten_schema(s: dict) -> dict:
            import copy
            s = copy.deepcopy(s)
            defs = s.pop("$defs", {})
            def replace_refs(obj):
                if isinstance(obj, dict):
                    if "$ref" in obj:
                        ref = obj.pop("$ref")
                        if ref.startswith("#/$defs/"):
                            def_name = ref.replace("#/$defs/", "")
                            obj.update(replace_refs(copy.deepcopy(defs[def_name])))
                        return obj
                    return {k: replace_refs(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [replace_refs(v) for v in obj]
                return obj
            return replace_refs(s)
            
        flat_schema = flatten_schema(schema)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": flat_schema,
                "temperature": kwargs.get("temperature", 0.2),
            }
        }
        
        if use_search_grounding:
            payload["tools"] = [{"googleSearch": {}}]

        global _last_request_time
        
        async with _gemini_semaphore:
            max_429_retries = 8
            base_429_delay = 10.0
            
            for attempt in range(max_429_retries + 1):
                now = time.time()
                elapsed = now - _last_request_time
                if elapsed < REQUEST_DELAY_SECONDS:
                    await asyncio.sleep(REQUEST_DELAY_SECONDS - elapsed)
                    
                try:
                    async with httpx.AsyncClient(timeout=kwargs.get("timeout", 120.0)) as client:
                        response = await client.post(url, json=payload, headers=headers)
                        _last_request_time = time.time()
                        
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
                    if e.response.status_code in (429, 500, 502, 503, 504) and attempt < max_429_retries:
                        delay = base_429_delay * (2 ** attempt)
                        log.warning(f"Gemini API {e.response.status_code} Limit/Error. Backing off for {delay}s...", attempt=attempt+1)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        log.warning("Gemini API returned error status", status_code=e.response.status_code, response=e.response.text)
                        raise e
                except httpx.RequestError as e:
                    if attempt < max_429_retries:
                        delay = base_429_delay * (2 ** attempt)
                        log.warning(f"Gemini API RequestError ({type(e).__name__}). Backing off for {delay}s...", attempt=attempt+1)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise e
                except Exception as e:
                    log.warning("Exception querying Gemini API for structured JSON", error=repr(e))
                    raise e
