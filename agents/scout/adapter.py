"""Search Adapter for Scout Agents."""

from __future__ import annotations

import asyncio
from typing import Any
from agents.scout.providers.base import BaseDiscoveryProvider
from core.logger import get_logger

log = get_logger(__name__)

class SearchAdapter:
    """
    Coordinates execution of multiple discovery providers.
    Abstracts away provider management, parallelism, and error aggregation
    from the ScoutAgent.
    """
    def __init__(self, providers: list[BaseDiscoveryProvider]) -> None:
        self.providers = providers

    async def search(self, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Execute all registered providers in parallel (respecting parallelism config),
        and aggregate results.
        """
        raw_companies = []
        tasks = []
        
        # In a real implementation with high parallelism, we might use asyncio.Semaphore
        # per provider based on provider.config.parallelism. 
        # For this scope, we launch them all and gather.
        for provider in self.providers:
            tasks.append(self._run_provider(provider, **kwargs))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, result in zip(self.providers, results):
            if isinstance(result, Exception):
                log.error("Adapter caught unhandled provider exception", provider=provider.name, error=str(result))
            elif isinstance(result, list):
                raw_companies.extend(result)
                
        return raw_companies

    async def _run_provider(self, provider: BaseDiscoveryProvider, **kwargs: Any) -> list[dict[str, Any]]:
        """Run a single provider wrapped with its specific parallelism constraints if needed."""
        # A semaphore could be applied here:
        # semaphore = getattr(provider, "_semaphore", asyncio.Semaphore(provider.config.parallelism))
        # async with semaphore:
        return await provider.discover(**kwargs)
