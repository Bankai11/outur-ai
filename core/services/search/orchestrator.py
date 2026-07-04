"""Lead Source Orchestrator to query multiple sources and merge results."""

import asyncio
from typing import Any

from core.logger import get_logger
from core.services.search.base import BaseSearchProvider, ProviderConfig
from core.services.search.metrics import CircuitBreaker, CircuitBreakerError
from core.services.search.confidence import ConfidenceEngine
from core.services.search.cache import SQLiteCache

from core.services.search.providers.google import GoogleSearchProvider
from core.services.search.providers.linkedin import LinkedInProvider

log = get_logger(__name__)


class LeadSourceOrchestrator:
    """
    Orchestrates searches across multiple lead generation and enrichment platforms.
    Merges and deduplicates results into a unified company/contact profile with evidence.
    """

    def __init__(self, providers: list[BaseSearchProvider] | None = None):
        self.cache = SQLiteCache()
        
        if providers:
            self.providers = providers
        else:
            # Default production providers
            self.providers = [
                GoogleSearchProvider(ProviderConfig(name="google"), cache=self.cache),
                LinkedInProvider(ProviderConfig(name="linkedin"), cache=self.cache)
            ]
            
        # Initialize circuit breakers for each provider
        self.circuit_breakers = {p.name: CircuitBreaker() for p in self.providers}

    async def _safe_call(self, provider: BaseSearchProvider, method_name: str, *args, **kwargs) -> Any:
        """Execute a provider method through its circuit breaker."""
        cb = self.circuit_breakers[provider.name]
        try:
            method = getattr(provider, method_name)
            return await cb.call(provider.name, method, *args, **kwargs)
        except CircuitBreakerError:
            log.warning(f"Skipping provider {provider.name} due to open circuit breaker.")
            return None
        except Exception as e:
            log.error(f"Provider {provider.name} failed during {method_name}: {str(e)}")
            return None

    async def search_company(self, domain_or_name: str) -> dict[str, Any]:
        """
        Search for a company across all configured sources.
        """
        log.info(f"Orchestrating company search for {domain_or_name}")
        
        tasks = [
            self._safe_call(provider, "search_company", domain_or_name)
            for provider in self.providers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        merged_profile = {
            "name": None,
            "domain": None,
            "industry": None,
            "description": None,
            "location": None,
            "evidence": []
        }
        
        for result in results:
            if isinstance(result, Exception) or not result:
                continue
                
            # Naive merge: first non-null wins for basic fields, but evidence accumulates
            if not merged_profile["name"] and result.get("name"):
                merged_profile["name"] = result["name"]
            if not merged_profile["domain"] and result.get("domain"):
                merged_profile["domain"] = result["domain"]
            if not merged_profile["industry"] and result.get("industry"):
                merged_profile["industry"] = result["industry"]
            if not merged_profile["description"] and result.get("description"):
                merged_profile["description"] = result["description"]
            
            if result.get("evidence"):
                merged_profile["evidence"].extend(result["evidence"])
                
        # Calculate a unified confidence score based on the ConfidenceEngine
        confidence = ConfidenceEngine.calculate_company_confidence(merged_profile)
        merged_profile["discovery_confidence"] = confidence
        
        return merged_profile

    async def search_contacts(self, company_domain: str, target_titles: list[str]) -> list[dict[str, Any]]:
        """
        Search for contacts at a company matching target titles across all sources.
        """
        log.info(f"Orchestrating contact search for {company_domain} with titles {target_titles}")
        
        tasks = [
            self._safe_call(provider, "search_contacts", company_domain, target_titles)
            for provider in self.providers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_contacts = []
        for result in results:
            if isinstance(result, Exception) or not result:
                continue
            if isinstance(result, list):
                # Optionally calculate confidence for each contact early
                for contact in result:
                    contact["discovery_confidence"] = ConfidenceEngine.calculate_contact_confidence(contact)
                all_contacts.extend(result)
                
        return all_contacts
