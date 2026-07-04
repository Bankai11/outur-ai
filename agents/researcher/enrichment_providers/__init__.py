"""Enrichment providers package for Outur AI Research Context Agent."""

from __future__ import annotations

from agents.researcher.enrichment_providers.base import BaseEnrichmentProvider
from agents.researcher.enrichment_providers.news import NewsEnrichmentProvider
from agents.researcher.enrichment_providers.social import SocialEnrichmentProvider
from agents.researcher.enrichment_providers.careers_analyser import CareersAnalyserProvider


class EnrichmentProviderRegistry:
    """
    Registry for managing company/contact enrichment providers dynamically.
    """

    def __init__(self) -> None:
        self._providers: list[BaseEnrichmentProvider] = []

    def register(self, provider: BaseEnrichmentProvider) -> None:
        """Register an enrichment provider."""
        if not any(p.name == provider.name for p in self._providers):
            self._providers.append(provider)

    def get_providers(self) -> list[BaseEnrichmentProvider]:
        """Get all registered providers."""
        return self._providers


# Global registry instance
enrichment_registry = EnrichmentProviderRegistry()

# Register defaults
enrichment_registry.register(NewsEnrichmentProvider())
enrichment_registry.register(SocialEnrichmentProvider())
enrichment_registry.register(CareersAnalyserProvider())

__all__ = [
    "BaseEnrichmentProvider",
    "NewsEnrichmentProvider",
    "SocialEnrichmentProvider",
    "CareersAnalyserProvider",
    "EnrichmentProviderRegistry",
    "enrichment_registry",
]
