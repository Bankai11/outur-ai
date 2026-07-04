"""Circuit breaker pattern implementation."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, Coroutine
import asyncio

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    """Exception raised when trying to execute while the circuit is open."""
    pass

class CircuitBreaker:
    """
    A simple Circuit Breaker to prevent cascading failures in providers.
    """
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0
        
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            
    def record_success(self) -> None:
        """Record a success and close the circuit if it was half-open."""
        self.failures = 0
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED

    def can_execute(self) -> bool:
        """Determine if an execution is allowed based on the current state."""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            # Check if cooldown has elapsed
            if time.time() - self.last_failure_time >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            # Only allow one test execution through in HALF_OPEN
            # To strictly enforce one execution, a more robust lock mechanism might be needed,
            # but for simple provider execution this is sufficient.
            return True
            
        return True
