"""
Integration tests for GET /health and GET /ready endpoints.

These tests use the AsyncClient fixture which hits the real FastAPI
ASGI app (no live server required) and validates:
- HTTP status codes
- Response body schema
- Required JSON fields
- X-Request-ID header presence
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for the GET /health (liveness) endpoint."""

    async def test_health_returns_200(self, async_client: AsyncClient) -> None:
        """Liveness endpoint must always return 200."""
        response = await async_client.get("/health")
        assert response.status_code == 200

    async def test_health_body_status_ok(self, async_client: AsyncClient) -> None:
        """Response body must contain status: ok."""
        response = await async_client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_contains_required_fields(self, async_client: AsyncClient) -> None:
        """Response must include app, version, environment, and timestamp."""
        response = await async_client.get("/health")
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data

    async def test_health_request_id_header(self, async_client: AsyncClient) -> None:
        """Every response must include an X-Request-ID header."""
        response = await async_client.get("/health")
        assert "x-request-id" in response.headers

    async def test_health_request_id_is_uuid(self, async_client: AsyncClient) -> None:
        """X-Request-ID must be a valid UUID string."""
        import uuid
        response = await async_client.get("/health")
        request_id = response.headers.get("x-request-id", "")
        # Should not raise
        uuid.UUID(request_id)

    async def test_health_app_name_matches_settings(self, async_client: AsyncClient) -> None:
        """app field in response should match the configured app name."""
        response = await async_client.get("/health")
        data = response.json()
        assert data["app"] == "Outur AI"


@pytest.mark.integration
class TestReadinessEndpoint:
    """
    Tests for the GET /ready (readiness) endpoint.

    Note: In the test environment the database is in-memory SQLite, so the
    DB check may pass or return 503 depending on setup. We test the shape
    of the response regardless of DB availability.
    """

    async def test_ready_returns_valid_status_code(self, async_client: AsyncClient) -> None:
        """Readiness must return either 200 (healthy) or 503 (degraded)."""
        response = await async_client.get("/ready")
        assert response.status_code in {200, 503}

    async def test_ready_body_has_status_field(self, async_client: AsyncClient) -> None:
        """Response body must always include a status field."""
        response = await async_client.get("/ready")
        data = response.json()
        assert "status" in data
        assert data["status"] in {"ok", "degraded", "unavailable"}

    async def test_ready_body_has_components(self, async_client: AsyncClient) -> None:
        """Response body must include a components dict."""
        response = await async_client.get("/ready")
        data = response.json()
        assert "components" in data
        assert isinstance(data["components"], dict)

    async def test_ready_has_request_id_header(self, async_client: AsyncClient) -> None:
        """Readiness endpoint must also return X-Request-ID."""
        response = await async_client.get("/ready")
        assert "x-request-id" in response.headers
