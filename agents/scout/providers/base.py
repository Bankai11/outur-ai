"""Base discovery provider definition."""

from __future__ import annotations

import time
import json
from abc import ABC, abstractmethod
from typing import Any

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential
from pydantic import TypeAdapter, ValidationError

from core.logger import get_logger
from core.llm.factory import get_llm_provider
from core.utils.cache import get_cached_response, set_cached_response
from core.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from agents.common.models import ProviderConfig, ProviderMetrics, CompanyOutputModel

log = get_logger(__name__)

# Standard schema for LLM generation
COMPANY_SCHEMA = {
    "type": "ARRAY",
    "description": "List of discovered companies matching the search parameters.",
    "items": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the company."},
            "website": {"type": "STRING", "description": "The company's primary website URL."},
            "linkedin_url": {"type": "STRING", "description": "The company's LinkedIn company page URL (if available)."},
            "industry": {"type": "STRING", "description": "The industry of the company (e.g. SaaS, FinTech)."},
            "location": {"type": "STRING", "description": "The company's headquarters location (e.g. New York, US)."},
            "careers_page": {"type": "STRING", "description": "The company's careers page URL (if available)."},
            "evidence": {
                "type": "ARRAY",
                "description": "List of sources proving this company exists and matches criteria. Crucial: Do not hallucinate.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "source_url": {"type": "STRING"},
                        "source_title": {"type": "STRING"},
                        "source_type": {"type": "STRING"},
                        "retrieved_at": {"type": "STRING"}
                    },
                    "required": ["source_url", "source_type"]
                }
            }
        },
        "required": ["name", "evidence"],
    }
}


class BaseDiscoveryProvider(ABC):
    """
    Abstract Base Class for all company discovery providers.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()
        self.metrics = ProviderMetrics()
        # Default circuit breaker: 3 failures, 60s cooldown
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique snake_case identifier for the provider.
        E.g. 'google_search', 'linkedin', 'manual_csv'.
        """
        ...

    @abstractmethod
    def build_prompt(self, **kwargs: Any) -> str:
        """
        Build the LLM prompt based on the provided search arguments.
        """
        ...

    def _normalize_company(self, company: dict[str, Any]) -> dict[str, Any]:
        """Normalize fields in the company dictionary."""
        if company.get("name"):
            company["name"] = company["name"].strip().title()
        if company.get("industry"):
            company["industry"] = company["industry"].strip().title()
        if company.get("location"):
            company["location"] = company["location"].strip().title()
        if company.get("website"):
            company["website"] = company["website"].strip().lower()
        return company

    async def discover(self, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Query the provider source for companies matching the filters.
        Wraps LLM calls with caching, metrics, circuit breaking, and Pydantic validation.
        """
        if not self.circuit_breaker.can_execute():
            self.metrics.healthy = False
            log.warning("Circuit breaker OPEN. Skipping execution.", provider=self.name)
            return []
            
        self.metrics.healthy = True
        prompt = self.build_prompt(**kwargs)
        
        # Check cache
        cached = await get_cached_response(prompt, COMPANY_SCHEMA)
        if cached is not None:
            log.info("Discovery cache hit", provider=self.name)
            return self._process_response(cached)

        # Execute LLM with configured retry
        start_time = time.time()
        self.metrics.requests += 1
        
        try:
            response = await self._execute_llm_with_retry(prompt)
            latency = (time.time() - start_time) * 1000
            
            # Update metrics
            self.metrics.latency_ms = (self.metrics.latency_ms * (self.metrics.requests - 1) + latency) / self.metrics.requests
            
            if response is None:
                self._record_failure("LLM returned None")
                return []
                
            self.circuit_breaker.record_success()
            
            # Cache the successful response
            await set_cached_response(prompt, COMPANY_SCHEMA, response, ttl_seconds=self.config.cache_ttl)
            
            return self._process_response(response)
            
        except Exception as e:
            self._record_failure(str(e))
            log.error("Provider execution failed completely", provider=self.name, error=str(e))
            return []
            
        finally:
            total_attempts = self.metrics.requests
            successful_attempts = total_attempts - self.metrics.failures
            self.metrics.success_rate = (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0.0

    def _record_failure(self, error_msg: str) -> None:
        self.metrics.failures += 1
        self.metrics.last_error = error_msg
        self.circuit_breaker.record_failure()

    async def _execute_llm_with_retry(self, prompt: str) -> list[Any] | dict[str, Any] | None:
        """Execute the LLM generation with automatic retries based on config."""
        llm = get_llm_provider()
        
        # Dynamic retry policy
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self.config.retry_limit),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        
        async for attempt in retryer:
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    self.metrics.retries += 1
                    
                res = await llm.generate_json(
                    prompt=prompt,
                    schema=COMPANY_SCHEMA,
                    use_search_grounding=True,
                    timeout=float(self.config.timeout_ms) / 1000.0
                )
                return res

    def _process_response(self, parsed: Any) -> list[dict[str, Any]]:
        """Process, validate with Pydantic, and normalize."""
        if not isinstance(parsed, list):
            return []
            
        adapter = TypeAdapter(list[CompanyOutputModel])
        valid_companies = []
        
        try:
            # First pass: Pydantic validation (this enforces structure and types)
            validated_models = adapter.validate_python(parsed)
        except ValidationError as e:
            log.error("Pydantic validation failed for provider output", provider=self.name, error=str(e))
            # Fallback to validating item by item to salvage valid records
            validated_models = []
            for item in parsed:
                try:
                    validated_models.append(CompanyOutputModel.model_validate(item))
                except ValidationError:
                    continue

        for model in validated_models:
            # Strict evidence check: Must have at least one valid source_url
            has_valid_evidence = any(bool(ev.source_url) for ev in model.evidence)
            
            if not has_valid_evidence:
                log.warning("Company dropped due to missing or invalid evidence", company_name=model.name)
                continue
                
            # Convert back to dict for normalization and standard usage
            comp_dict = model.model_dump()
            comp_dict = self._normalize_company(comp_dict)
            comp_dict["source"] = self.name
            valid_companies.append(comp_dict)
            
        return valid_companies
