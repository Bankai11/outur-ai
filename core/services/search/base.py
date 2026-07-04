"""Base abstractions for Lead Discovery Search Providers."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field

class ProviderConfig(BaseModel):
    """Configuration for a search provider."""
    name: str
    timeout_seconds: int = Field(default=10)
    max_retries: int = Field(default=3)
    parallelism: int = Field(default=5)
    cache_ttl_seconds: int = Field(default=86400) # 24 hours


class BaseCache(ABC):
    """Abstract base class for provider caching."""
    
    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a value from the cache."""
        pass
        
    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Set a value in the cache with an optional TTL."""
        pass


class BaseSearchProvider(ABC):
    """
    Abstract base class that all production search providers must inherit from.
    Enforces a consistent interface for the LeadSourceOrchestrator.
    """
    
    def __init__(self, config: ProviderConfig, cache: BaseCache | None = None):
        self.config = config
        self.cache = cache
        
    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def search_company(self, domain_or_name: str) -> dict[str, Any] | None:
        """
        Search for a company and return a normalized dict matching the expected schema.
        Should return None if no conclusive results are found.
        """
        pass

    @abstractmethod
    async def search_contacts(self, company_domain: str, target_titles: list[str]) -> list[dict[str, Any]]:
        """
        Search for contacts matching target titles at a company.
        Returns a list of normalized contact dicts.
        """
        pass
