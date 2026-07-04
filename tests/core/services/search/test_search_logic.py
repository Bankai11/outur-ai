import pytest
from core.services.search.metrics import CircuitBreaker, CircuitBreakerError
from core.services.search.confidence import ConfidenceEngine


@pytest.mark.asyncio
async def test_circuit_breaker():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=1)
    
    async def failing_func():
        raise ValueError("Simulated failure")
        
    async def success_func():
        return "Success"
        
    # 1. First failure
    with pytest.raises(ValueError):
        await breaker.call("test_provider", failing_func)
    assert breaker.state == "CLOSED"
    assert breaker.metrics.total_errors == 1
    
    # 2. Second failure triggers OPEN
    with pytest.raises(ValueError):
        await breaker.call("test_provider", failing_func)
    assert breaker.state == "OPEN"
    assert breaker.metrics.healthy is False
    
    # 3. Third call immediately fails without executing func
    with pytest.raises(CircuitBreakerError):
        await breaker.call("test_provider", success_func)
        

def test_confidence_engine_company():
    profile = {
        "name": "Apple",
        "domain": "apple.com",
        "evidence": [
            {"source_type": "google"},
            {"source_type": "linkedin"}
        ]
    }
    
    score = ConfidenceEngine.calculate_company_confidence(profile)
    # google (30) + linkedin (20) + corroboration (1*10) + domain match (15) = 75
    assert score == 75


def test_confidence_engine_contact():
    contact = {
        "email": "steve@apple.com",
        "source_evidence": {"source_type": "apollo"},
        "verification_status": "verified"
    }
    
    score = ConfidenceEngine.calculate_contact_confidence(contact)
    # apollo (15) + email present (20) + verified (50) = 85
    assert score == 85
