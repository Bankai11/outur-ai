from __future__ import annotations

import json
from typing import Any

from agents.enrichment.models import EnrichmentResult

class EnrichmentCache:
    """
    Interface for caching enrichment results.
    """

    async def get(self, key: str) -> EnrichmentResult | None:
        pass

    async def set(self, key: str, data: EnrichmentResult, ttl_seconds: int = 86400) -> None:
        pass


class InMemoryEnrichmentCache(EnrichmentCache):
    """
    Simple in-memory cache for development.
    """
    
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    async def get(self, key: str) -> EnrichmentResult | None:
        data = self._cache.get(key)
        if data:
            return EnrichmentResult.model_validate_json(data)
        return None

    async def set(self, key: str, data: EnrichmentResult, ttl_seconds: int = 86400) -> None:
        self._cache[key] = data.model_dump_json()


class RedisEnrichmentCache(EnrichmentCache):
    """
    Redis implementation for production caching.
    """
    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    async def get(self, key: str) -> EnrichmentResult | None:
        if not self.redis:
            return None
        data = await self.redis.get(key)
        if data:
            return EnrichmentResult.model_validate_json(data)
        return None

    async def set(self, key: str, data: EnrichmentResult, ttl_seconds: int = 86400) -> None:
        if not self.redis:
            return
        await self.redis.set(key, data.model_dump_json(), ex=ttl_seconds)
