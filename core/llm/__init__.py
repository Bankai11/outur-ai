"""LLM package with abstracted providers and factories."""

from __future__ import annotations

from core.llm.base import BaseLLMProvider
from core.llm.gemini import GeminiLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory to retrieve the default active LLM provider.
    """
    return GeminiLLMProvider()


__all__ = ["BaseLLMProvider", "GeminiLLMProvider", "get_llm_provider"]
