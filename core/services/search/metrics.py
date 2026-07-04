"""Provider metrics and circuit breaker implementation."""

import time
from typing import Any
from functools import wraps
from pydantic import BaseModel, Field

from core.logger import get_logger

log = get_logger(__name__)


class ProviderMetrics(BaseModel):
    """Real-time health reporting for a provider."""
    healthy: bool = True
    last_error: str | None = None
    last_error_time: float | None = None
    total_calls: int = 0
    total_errors: int = 0
    success_rate: float = 100.0
    average_latency: float = 0.0
    
    def record_success(self, latency: float):
        """Update metrics for a successful call."""
        self.total_calls += 1
        
        # Exponential moving average for latency
        if self.average_latency == 0.0:
            self.average_latency = latency
        else:
            self.average_latency = (self.average_latency * 0.9) + (latency * 0.1)
            
        self._update_success_rate()
        
    def record_error(self, error_msg: str):
        """Update metrics for a failed call."""
        self.total_calls += 1
        self.total_errors += 1
        self.last_error = error_msg
        self.last_error_time = time.time()
        self._update_success_rate()
        
    def _update_success_rate(self):
        if self.total_calls > 0:
            self.success_rate = ((self.total_calls - self.total_errors) / self.total_calls) * 100.0


class CircuitBreakerError(Exception):
    """Exception raised when the circuit breaker is open (tripped)."""
    pass


class CircuitBreaker:
    """
    Prevents calling a provider if it has been failing consistently.
    Wraps provider calls and maintains an open/closed state.
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED" # CLOSED = healthy, OPEN = failing
        self.metrics = ProviderMetrics()
        
    def _evaluate_state(self) -> str:
        """Determine if the circuit should be closed or opened."""
        if self.state == "OPEN":
            # Check if enough time has passed to try again (transition to HALF_OPEN effectively)
            if time.time() - self.last_failure_time > self.recovery_timeout_seconds:
                self.state = "CLOSED"
                self.failures = 0 # Reset to allow a retry
                self.metrics.healthy = True
                log.info("Circuit breaker reset - attempting recovery.")
        return self.state

    def record_failure(self, error: Exception):
        """Record a failure and optionally open the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()
        self.metrics.record_error(str(error))
        
        if self.failures >= self.failure_threshold:
            if self.state == "CLOSED":
                log.warning(f"Circuit breaker TRIPPED! Provider exceeded {self.failure_threshold} failures.")
            self.state = "OPEN"
            self.metrics.healthy = False
            
    def record_success(self, latency: float):
        """Record a success and reset failures."""
        self.failures = 0
        self.state = "CLOSED"
        self.metrics.healthy = True
        self.metrics.record_success(latency)

    async def call(self, provider_name: str, func, *args, **kwargs) -> Any:
        """
        Execute the async function through the circuit breaker.
        Throws CircuitBreakerError if the circuit is OPEN.
        """
        if self._evaluate_state() == "OPEN":
            raise CircuitBreakerError(f"Circuit breaker is OPEN for provider: {provider_name}")
            
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            latency = time.time() - start_time
            self.record_success(latency)
            return result
        except Exception as e:
            self.record_failure(e)
            raise
