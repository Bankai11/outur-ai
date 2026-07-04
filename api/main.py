"""
FastAPI application factory for Outur AI.

Architecture
------------
- ``create_app()`` is the factory function — it builds and configures the app.
  This pattern makes testing easy: tests can call ``create_app()`` with overrides.
- The ``lifespan`` context manager handles startup/shutdown events cleanly.
- Middleware is registered in a specific order (outermost first).
- All routers are mounted under ``/api/v1`` for versioning.

Running locally
---------------
::

    uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from api.middleware.logging import RequestLoggingMiddleware
from api.routers import health, companies, campaigns, webhooks, dashboard
from core.config import get_settings
from core.database import check_db_connection, engine
from core.logger import configure_logging, get_logger
from core.utils.exceptions import OUTURAIError

log = get_logger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan — startup & shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup:  configure logging, verify DB connectivity.
    Shutdown: dispose the connection pool gracefully.
    """
    # ── Startup ──────────────────────────────────────────────────────────
    configure_logging()
    log.info(
        "Starting Outur AI",
        version=settings.app_version,
        env=settings.app_env.value,
    )

    db_ok = await check_db_connection()
    if db_ok:
        log.info("Database connection verified")
    else:
        log.warning("Database unreachable at startup — continuing anyway")

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────
    log.info("Shutting down Outur AI — disposing database pool")
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Exception handlers
# ─────────────────────────────────────────────────────────────────────────────

async def outur_exception_handler(request: object, exc: OUTURAIError) -> ORJSONResponse:
    """Convert all OUTURAIError subclasses to structured JSON HTTP responses."""
    log.warning(
        "Application error",
        error_code=exc.error_code,
        detail=exc.detail,
        status_code=exc.status_code,
        context=exc.context,
    )
    return ORJSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Returns
    -------
    FastAPI
        A fully configured application instance ready to serve requests.
    """
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Outur AI — Production-grade AI Business Development Platform.\n\n"
            "Automates lead discovery, enrichment, research, and personalised outreach "
            "using a multi-agent pipeline powered by Google Gemini."
        ),
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,  # Faster JSON serialisation
        lifespan=lifespan,
    )

    # ── Middleware (applied outermost → innermost) ─────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ─────────────────────────────────────────────────
    app.add_exception_handler(OUTURAIError, outur_exception_handler)  # type: ignore[arg-type]

    # ── Routers ────────────────────────────────────────────────────────────
    # Health check — no prefix (needed by load balancers at root level)
    app.include_router(health.router, tags=["Health"])

    # Versioned routers
    app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
    app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["Campaigns"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    # app.include_router(leads.router,     prefix="/api/v1/leads",     tags=["Leads"])

    # Mount static files for the dashboard
    import os
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Module-level app instance (used by uvicorn)
# ─────────────────────────────────────────────────────────────────────────────

app: FastAPI = create_app()
