"""Base contact provider definition."""

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
from core.utils.circuit_breaker import CircuitBreaker
from agents.common.evidence import ConfidenceEngine
from agents.common.models import ProviderConfig, ProviderMetrics, ContactOutputModel

log = get_logger(__name__)

# Standard schema for LLM generation
CONTACTS_SCHEMA = {
    "type": "ARRAY",
    "description": "List of discovered contacts working at the company.",
    "items": {
        "type": "OBJECT",
        "properties": {
            "full_name": {"type": "STRING", "description": "Full name of the contact."},
            "job_title": {"type": "STRING", "description": "Current job title."},
            "email": {"type": "STRING", "description": "Email address (if available)."},
            "linkedin_url": {"type": "STRING", "description": "LinkedIn profile URL (if available)."},
            "location": {"type": "STRING", "description": "Location of the contact (if available)."},
            "evidence": {
                "type": "ARRAY",
                "description": "List of sources proving this contact works at the company.",
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
        "required": ["full_name", "evidence"],
    }
}


class BaseContactProvider(ABC):
    """
    Abstract Base Class for all contact discovery providers.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()
        self.metrics = ProviderMetrics()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        self.confidence_engine = ConfidenceEngine()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique snake_case identifier for the provider.
        """
        ...

    @abstractmethod
    def build_prompt(self, **kwargs: Any) -> str:
        """
        Build the LLM prompt based on the provided search arguments.
        """
        ...

    def _normalize_contact(self, contact: dict[str, Any]) -> dict[str, Any]:
        """Normalize fields in the contact dictionary."""
        if contact.get("full_name"):
            contact["full_name"] = contact["full_name"].strip().title()
        if contact.get("job_title"):
            contact["job_title"] = contact["job_title"].strip().title()
        if contact.get("email"):
            contact["email"] = contact["email"].strip().lower()
        if contact.get("location"):
            contact["location"] = contact["location"].strip().title()
        return contact

    async def discover_contacts(self, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Query the provider source for contacts.
        Wraps LLM calls with caching, metrics, circuit breaking, and Pydantic validation.
        """
        if not self.circuit_breaker.can_execute():
            self.metrics.healthy = False
            log.warning("Circuit breaker OPEN. Skipping execution.", provider=self.name)
            return []
            
        self.metrics.healthy = True
        prompt = self.build_prompt(**kwargs)
        
        cached = await get_cached_response(prompt, CONTACTS_SCHEMA)
        if cached is not None:
            log.info("Contact discovery cache hit", provider=self.name)
            return self._process_response(cached, kwargs)

        start_time = time.time()
        self.metrics.requests += 1
        
        try:
            response = await self._execute_llm_with_retry(prompt)
            latency = (time.time() - start_time) * 1000
            
            self.metrics.latency_ms = (self.metrics.latency_ms * (self.metrics.requests - 1) + latency) / self.metrics.requests
            
            if response is None:
                self._record_failure("LLM returned None")
                return []
                
            self.circuit_breaker.record_success()
            await set_cached_response(prompt, CONTACTS_SCHEMA, response, ttl_seconds=self.config.cache_ttl)
            
            return self._process_response(response, kwargs)
            
        except Exception as e:
            self._record_failure(str(e))
            log.error("Contact provider execution failed completely", provider=self.name, error=str(e))
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
                    schema=CONTACTS_SCHEMA,
                    use_search_grounding=True,
                    timeout=float(self.config.timeout_ms) / 1000.0
                )
                return res

    def _process_response(self, parsed: Any, search_kwargs: dict[str, Any]) -> list[dict[str, Any]]:
        """Process, validate with Pydantic, normalize, and calculate confidence."""
        if not isinstance(parsed, list):
            return []
            
        adapter = TypeAdapter(list[ContactOutputModel])
        valid_contacts = []
        total_confidence = 0
        
        try:
            validated_models = adapter.validate_python(parsed)
        except ValidationError as e:
            log.error("Pydantic validation failed for contact output", provider=self.name, error=str(e))
            validated_models = []
            for item in parsed:
                try:
                    validated_models.append(ContactOutputModel.model_validate(item))
                except ValidationError:
                    continue

        # Extract extra signals like email verification if provided in kwargs
        additional_signals = {}
        if search_kwargs.get("email_verified"):
            additional_signals["email_verified"] = True

        for model in validated_models:
            has_valid_evidence = any(bool(ev.source_url) for ev in model.evidence)
            
            if not has_valid_evidence:
                log.warning("Contact dropped due to missing or invalid evidence", contact_name=model.full_name)
                continue
                
            comp_dict = model.model_dump()
            comp_dict = self._normalize_contact(comp_dict)
            
            # Calculate confidence using the ConfidenceEngine
            confidence = self.confidence_engine.evaluate(comp_dict["evidence"], additional_signals)
            comp_dict["confidence_score"] = confidence
            comp_dict["source"] = self.name
            
            valid_contacts.append(comp_dict)
            total_confidence += confidence
            
        if valid_contacts:
            avg_conf = total_confidence / len(valid_contacts)
            current_avg = self.metrics.average_confidence
            # Simple moving average for the metric
            self.metrics.average_confidence = (current_avg + avg_conf) / 2 if current_avg > 0 else avg_conf
            
        return valid_contacts
