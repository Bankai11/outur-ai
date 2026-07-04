"""Base enrichment provider definition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseEnrichmentProvider(ABC):
    """
    Abstract Base Class for all company/contact enrichment providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique snake_case identifier for the provider.
        E.g. 'news', 'social', 'careers_analyser'.
        """
        ...

    @abstractmethod
    async def enrich(
        self,
        company_name: str,
        domain: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Fetch enrichment details.

        Parameters
        ----------
        company_name:
            The name of the company.
        domain:
            The domain name of the company.
        **kwargs:
            Additional enrichment-specific options.

        Returns
        -------
        dict[str, Any]
            Dict of found signals / text context.
        """
        ...
