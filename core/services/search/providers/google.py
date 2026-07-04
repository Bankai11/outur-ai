"""Google Search Provider Implementation."""

import os
import time
from typing import Any
import httpx

from core.logger import get_logger
from core.services.search.base import BaseSearchProvider, ProviderConfig, BaseCache

log = get_logger(__name__)


class GoogleSearchProvider(BaseSearchProvider):
    """
    Search provider that uses the Google Custom Search JSON API.
    """
    
    def __init__(self, config: ProviderConfig, cache: BaseCache | None = None):
        super().__init__(config, cache)
        # Using environment variables for API keys in a production system.
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "")
        self.cx = os.getenv("GOOGLE_SEARCH_CX", "")
        
    async def _fetch_from_api(self, query: str) -> list[dict[str, Any]]:
        """Fetch results directly from the Google API."""
        if not self.api_key or not self.cx:
            log.warning("Google Search API key or CX not configured. Returning empty results.")
            return []
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": 3,
        }
        
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])

    async def search_company(self, domain_or_name: str) -> dict[str, Any] | None:
        """Search for a company via Google."""
        cache_key = f"google:company:{domain_or_name}"
        
        if self.cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                log.info(f"Cache hit for Google search company: {domain_or_name}")
                return cached_result
                
        # If cache misses, call the actual API
        results = await self._fetch_from_api(domain_or_name)
        
        if not results:
            return None
            
        # Parse the first useful result as the primary company description
        first_item = results[0]
        
        # We would typically use an LLM here to extract structured JSON from the snippets.
        # For this implementation, we map it to the expected schema.
        parsed_result = {
            "name": domain_or_name, # Fallback to query
            "domain": None,
            "industry": None, # Google Custom Search rarely gives clean industry tags
            "description": first_item.get("snippet", ""),
            "evidence": [{
                "source_type": "google",
                "source_url": first_item.get("link", ""),
                "source_title": first_item.get("title", ""),
                "retrieved_at": time.time()
            }]
        }
        
        if self.cache:
            await self.cache.set(cache_key, parsed_result, ttl=self.config.cache_ttl_seconds)
            
        return parsed_result

    async def search_contacts(self, company_domain: str, target_titles: list[str]) -> list[dict[str, Any]]:
        """Google is typically poor for finding specific structured contacts."""
        # We rely on LinkedIn, Apollo, or Hunter for direct contact searches.
        return []
