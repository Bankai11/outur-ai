"""Models for discovery providers."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, HttpUrl

class ProviderConfig(BaseModel):
    """Configuration for a discovery provider."""
    retry_limit: int = Field(default=3, description="Maximum number of retries.")
    timeout_ms: int = Field(default=30000, description="Timeout in milliseconds for LLM calls.")
    cache_ttl: int = Field(default=86400, description="Time to live for cache entries in seconds.")
    parallelism: int = Field(default=1, description="Maximum concurrent requests allowed for this provider.")

class ProviderMetrics(BaseModel):
    """Metrics tracking for a discovery provider."""
    healthy: bool = Field(default=True, description="Whether the provider is currently healthy.")
    last_error: Optional[str] = Field(default=None, description="The last error message encountered.")
    latency_ms: float = Field(default=0.0, description="Moving average latency in milliseconds.")
    success_rate: float = Field(default=0.0, description="Success rate percentage (0-100).")
    requests: int = Field(default=0, description="Total number of requests made.")
    failures: int = Field(default=0, description="Total number of failed requests.")
    retries: int = Field(default=0, description="Total number of retries performed.")
    average_confidence: float = Field(default=0.0, description="Average confidence score of discovered records.")


class EvidenceModel(BaseModel):
    """Strict model for validating evidence of a discovered entity."""
    source_url: str
    source_title: Optional[str] = None
    source_type: str
    retrieved_at: Optional[str] = None


class CompanyOutputModel(BaseModel):
    """Strict model for validating LLM output for a discovered company."""
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    careers_page: Optional[str] = None
    evidence: list[EvidenceModel] = Field(default_factory=list)


class ContactOutputModel(BaseModel):
    """Strict model for validating LLM output for a discovered contact."""
    full_name: str
    job_title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    location: Optional[str] = None
    evidence: list[EvidenceModel] = Field(default_factory=list)
