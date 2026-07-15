import base64
import hashlib
import hmac
import time
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agents.campaign_execution.models import ProviderConfig
from agents.campaign_execution.providers import MockProvider, get_circuit_breaker
from core.config import get_settings


@pytest.mark.anyio
async def test_correlation_id_middleware(async_client: AsyncClient):
    """
    Verify that correlation and request IDs are generated, propagated,
    and returned in headers correctly.
    """
    # 1. Without input headers: should auto-generate
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers

    req_id = response.headers["X-Request-ID"]
    corr_id = response.headers["X-Correlation-ID"]
    assert len(req_id) > 0
    assert len(corr_id) > 0
    assert req_id == corr_id  # Correlation falls back to request ID if none supplied

    # 2. With input X-Correlation-ID header: should propagate
    input_corr_id = f"test-corr-{uuid4()}"
    response2 = await async_client.get("/health", headers={"X-Correlation-ID": input_corr_id})
    assert response2.status_code == 200
    assert response2.headers["X-Correlation-ID"] == input_corr_id
    assert response2.headers["X-Request-ID"] != input_corr_id  # Request ID is still unique


@pytest.mark.anyio
async def test_health_check_readiness(async_client: AsyncClient):
    """
    Verify health and readiness endpoints.
    """
    # Liveness
    res_health = await async_client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "ok"

    # Readiness (will execute Postgres and Redis check)
    res_ready = await async_client.get("/ready")
    # Depends on test DB/Redis environment availability (can be 200 or 503)
    assert res_ready.status_code in (200, 503)
    data_ready = res_ready.json()
    assert "database" in data_ready["components"]
    assert "redis" in data_ready["components"]
    assert "llm_provider" in data_ready["components"]


@pytest.mark.anyio
async def test_metrics_endpoint(async_client: AsyncClient):
    """
    Verify system metrics aggregation endpoint.
    """
    res = await async_client.get("/api/v1/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "queue" in data
    assert "deliveries" in data
    assert "webhooks" in data
    assert "queue_depth" in data["queue"]


@pytest.mark.anyio
async def test_webhook_signature_validation(async_client: AsyncClient):
    """
    Verify webhook signature validation is enforced and rejects bad requests.
    """
    settings = get_settings()
    # Configure a mock secret in settings for the test
    original_secret = settings.resend_webhook_signing_secret
    # base64 encoded "test-secret"
    settings.resend_webhook_signing_secret = "whsec_dGVzdC1zZWNyZXQ="

    payload = b'{"type": "email.sent", "data": {"email_id": "test-email-123"}}'

    try:
        # 1. Request without headers should fail
        res = await async_client.post("/api/v1/webhooks/resend", content=payload)
        assert res.status_code == 401

        # 2. Request with invalid signature should fail
        headers = {
            "svix-id": "msg_xyz",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,badsignaturehash"
        }
        res2 = await async_client.post("/api/v1/webhooks/resend", content=payload, headers=headers)
        assert res2.status_code == 401

        # 3. Request with valid signature should pass or report unknown email
        ts = str(int(time.time()))
        to_sign = f"msg_xyz.{ts}.".encode() + payload
        secret_bytes = base64.b64decode("dGVzdC1zZWNyZXQ=")
        computed_sig = hmac.new(secret_bytes, to_sign, hashlib.sha256).hexdigest()

        valid_headers = {
            "svix-id": "msg_xyz",
            "svix-timestamp": ts,
            "svix-signature": f"v1,{computed_sig}"
        }
        res3 = await async_client.post(
            "/api/v1/webhooks/resend",
            content=payload,
            headers=valid_headers
        )
        assert res3.status_code == 200
        assert res3.json()["status"] == "success"

    finally:
        settings.resend_webhook_signing_secret = original_secret


@pytest.mark.anyio
async def test_circuit_breaker_delivery_provider():
    """
    Verify that sequential transient failures trip the circuit breaker.
    """
    config = ProviderConfig(
        provider_name="mock_circuit_breaker_test",
        max_retries=1,
        rate_limit_per_minute=10
    )

    provider = MockProvider(config)
    cb = get_circuit_breaker("mock_circuit_breaker_test")
    cb.failures = 0
    cb.state = cb.state.CLOSED

    # Should be allowed to execute
    assert cb.can_execute() is True

    # 1. Perform 3 consecutive transient timeout calls to trip the breaker
    for _ in range(3):
        res = await provider.send_email(
            to_email="timeout@example.com",
            subject="Test subject",
            body="Test body"
        )
        assert res.success is False
        assert "timeout" in res.error

    # 2. Breaker should now be open
    assert cb.can_execute() is False

    # 3. Next execution should fail fast with Circuit Breaker error
    res_fast = await provider.send_email(
        to_email="test@example.com",
        subject="Test subject",
        body="Test body"
    )
    assert res_fast.success is False
    assert "Circuit breaker is OPEN" in res_fast.error
