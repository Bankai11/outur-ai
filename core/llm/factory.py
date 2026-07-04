"""Factory for creating LLM providers."""

from __future__ import annotations

from core.llm.base import BaseLLMProvider
from core.llm.gemini import GeminiLLMProvider
from core.config import get_settings


def get_llm_provider() -> BaseLLMProvider:
    """
    Get the configured LLM provider instance.
    Currently returns GeminiLLMProvider, but can be extended based on configuration.
    """
    # E.g. settings = get_settings()
    # if settings.llm_provider == "openai": ...
    return GeminiLLMProvider()
