"""Web Search discovery provider using real search engines."""

from __future__ import annotations

import json
from typing import Any

from agents.scout.providers.base import BaseDiscoveryProvider
from core.services.search.tavily_provider import TavilySearchProvider
from core.logger import get_logger

logger = get_logger(__name__)


class WebSearchProvider(BaseDiscoveryProvider):
    """
    Discovers companies using a real Web Search Provider (Tavily).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_provider = TavilySearchProvider()

    @property
    def name(self) -> str:
        return "web_search"

    async def discover(self, **kwargs: Any) -> list[dict[str, Any]]:
        industry = kwargs.get("industry") or "SaaS"
        location = kwargs.get("location") or "Global"
        company_size = kwargs.get("company_size") or ""
        
        # Step 1: Perform real web search
        query = f"top {industry} companies in {location} hiring {company_size}"
        search_results = await self.search_provider.search(query, limit=10)
        
        if not search_results:
            logger.warning("No search results returned from provider.")
            return []
            
        # Step 2: Feed real data to LLM for structuring
        self._search_results_context = json.dumps(search_results, indent=2)
        
        # Proceed with normal LLM structured generation
        results = await super().discover(**kwargs)
        for company in results:
            company["source"] = self.name
        return results

    def build_prompt(self, **kwargs: Any) -> str:
        return (
            "Extract a list of companies from the following real search results. "
            "For each company, provide its name, website, industry, location, and strict evidence (URLs). "
            "Do NOT hallucinate companies. Only extract from the provided search results.\n\n"
            f"Search Results:\n{self._search_results_context}"
        )
