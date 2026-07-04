"""
Health and readiness check endpoints.

Endpoints
---------
GET /health
    Liveness probe — returns 200 as long as the app process is running.
    Used by Docker HEALTHCHECK and Kubernetes liveness probes.

GET /ready
    Readiness probe — returns 200 only when all critical dependencies
    (database, etc.) are reachable.
    Used by Kubernetes readiness probes and load balancers.

Response schema follows the IETF Health Check Response Format (RFC draft):
https://tools.ietf.org/html/draft-inadarei-api-health-check
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from core.config import get_settings
from core.database import check_db_connection
from core.logger import get_logger

log = get_logger(__name__)
router = APIRouter()
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class ComponentStatus(BaseModel):
    """Status of a single external dependency."""

    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """Full health check response body."""

    status: Literal["ok", "degraded", "unavailable"]
    app: str
    version: str
    environment: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    components: dict[str, ComponentStatus] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description=(
        "Always returns **200 OK** when the application process is running. "
        "Does **not** check external dependencies."
    ),
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """
    Liveness endpoint.

    Returns 200 immediately — no I/O performed.
    If this endpoint fails, the process is dead and should be restarted.
    """
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Checks all critical dependencies. Returns **200** when the app is ready "
        "to serve traffic, **503** when degraded or unavailable."
    ),
    tags=["Health"],
    responses={
        200: {"description": "All dependencies healthy"},
        503: {"description": "One or more dependencies unavailable"},
    },
)
async def readiness_check() -> ORJSONResponse:
    """
    Readiness endpoint.

    Performs real I/O checks:
    - PostgreSQL connectivity

    Returns 200 when all checks pass, 503 with detail when any fail.
    """
    import time

    components: dict[str, ComponentStatus] = {}
    overall_ok = True

    # ── Database ──────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    db_ok = await check_db_connection()
    db_latency = round((time.perf_counter() - t0) * 1000, 2)

    components["database"] = ComponentStatus(
        status="ok" if db_ok else "unavailable",
        latency_ms=db_latency,
        detail=None if db_ok else "PostgreSQL connection failed",
    )
    if not db_ok:
        overall_ok = False
        log.warning("Readiness check: database unavailable", latency_ms=db_latency)

    # ── Add future checks here (Redis, external APIs, etc.) ───────────────

    status: Literal["ok", "unavailable"] = "ok" if overall_ok else "unavailable"
    http_status = 200 if overall_ok else 503

    body = HealthResponse(
        status=status,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
        components=components,
    )

    return ORJSONResponse(status_code=http_status, content=body.model_dump())
