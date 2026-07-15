from __future__ import annotations

import asyncio
from typing import Any

from agents.enrichment.models import EnrichmentResult
from agents.enrichment.providers import EnrichmentProvider
from agents.enrichment.cache import EnrichmentCache
from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact

log = get_logger(__name__)


class EnrichmentService:
    """
    Orchestrates enrichment providers and caching.
    Supports merging data from multiple providers.
    """
    
    def __init__(
        self,
        providers: list[EnrichmentProvider],
        cache: EnrichmentCache
    ) -> None:
        self.providers = providers
        self.cache = cache

    async def enrich(
        self,
        company: Company,
        contacts: list[Contact],
        force_refresh: bool = False
    ) -> EnrichmentResult:
        """
        Enrich a company and its contacts using the configured providers.
        """
        # 1. Check Cache
        cache_key = f"enrichment:company:{company.id}"
        if not force_refresh:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                log.info("Enrichment cache hit", company_id=str(company.id))
                return cached_result
        
        log.info("Enrichment cache miss, fetching from providers", company_id=str(company.id))

        # 2. Fetch from Providers (concurrently or sequentially depending on needs)
        # We will do sequential fallback or merging depending on strategy.
        # Here we just use the first provider that succeeds to keep it simple, 
        # but the architecture allows merging multiple later.
        
        final_result = EnrichmentResult()
        
        for provider in self.providers:
            try:
                log.debug(f"Calling provider {provider.name}", company_id=str(company.id))
                result = await provider.enrich(company, contacts)
                
                # Merge into final result (simple overwrite for now)
                if result.company_enrichment:
                    final_result.company_enrichment = result.company_enrichment
                
                if result.contact_enrichment:
                    final_result.contact_enrichment.update(result.contact_enrichment)
                
                if result.raw_data:
                    final_result.raw_data = final_result.raw_data or {}
                    final_result.raw_data[provider.name] = result.raw_data

                # Break after first successful full provider, or continue to merge.
                # Here we assume a single provider handles it for the mock.
                break
                
            except Exception as e:
                log.error("Provider enrichment failed", provider=provider.name, error=str(e))
                # Do not crash, continue to next provider
                continue

        # 3. Cache the result
        if final_result.company_enrichment or final_result.contact_enrichment:
            await self.cache.set(cache_key, final_result)
        
        return final_result
