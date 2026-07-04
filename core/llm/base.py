"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """
    Abstract Base Class representing an LLM Provider.
    """

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        use_search_grounding: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Generate structured JSON output from a prompt.

        Parameters
        ----------
        prompt:
            Text prompt instructions for the LLM.
        schema:
            JSON schema dictionary enforcing the output structure.
        use_search_grounding:
            If True, the LLM should use an external search tool for evidence.
        **kwargs:
            Optional generation settings (temperature, models, etc.)

        Returns
        -------
        dict[str, Any] | list[Any] | None
            Parsed JSON output, or None if generation failed.
        """
        ...
