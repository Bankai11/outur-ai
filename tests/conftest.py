"""
Pytest configuration and shared fixtures for the Outur AI test suite.

Fixture hierarchy
-----------------
settings_override  →  Returns a Settings instance with test-safe values.
app                →  FastAPI app with dependency overrides applied.
async_client       →  Async httpx TestClient for integration tests.
db_session         →  Async in-memory SQLite session (no real DB needed for unit tests).

Markers
-------
pytest.ini configures three markers:
  @pytest.mark.unit        — Pure unit tests (no I/O, no DB)
  @pytest.mark.integration — Tests requiring a running database
  @pytest.mark.e2e         — Full end-to-end tests (use sparingly)
"""

from __future__ import annotations

import os
# Force test environment variables before settings are imported/loaded
os.environ["APP_ENV"] = "testing"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"
os.environ["APP_SECRET_KEY"] = "test-secret-key-must-be-at-least-32-chars"
os.environ["JWT_SECRET_KEY"] = "test-jwt-key-must-be-at-least-32-chars!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Clean up stale test cache db
if os.path.exists(".outur_cache_test.db"):
    try:
        os.remove(".outur_cache_test.db")
    except OSError:
        pass

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from core.config import Settings, get_settings
from core.database import Base, get_async_session


# ─────────────────────────────────────────────────────────────────────────────
# Settings override
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Return a Settings instance with safe test defaults.

    Uses an in-memory SQLite URL so unit tests never touch a real database.
    Clears the lru_cache before and after to avoid polluting other tests.
    """
    get_settings.cache_clear()
    settings = Settings(
        _env_file=None,
        app_env="testing",
        app_debug=True,
        app_secret_key="test-secret-key-must-be-at-least-32-chars",
        jwt_secret_key="test-jwt-key-must-be-at-least-32-chars!!",
        database_url="sqlite+aiosqlite:///:memory:",
        log_level="DEBUG",
        log_format="console",
        gemini_api_key="test-key",
        resend_webhook_signing_secret="whsec_dGVzdC1zZWNyZXQ=",
    )
    yield settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_get_settings(test_settings: Settings):
    """Globally override get_settings for all tests to avoid loading local .env secrets."""
    from unittest.mock import patch
    with patch("core.config.get_settings", return_value=test_settings):
        yield



# ─────────────────────────────────────────────────────────────────────────────
# In-memory database (SQLite)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_engine(test_settings: Settings) -> AsyncGenerator[Any, None]:
    """Create a fresh in-memory SQLite engine per test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh async database session backed by in-memory SQLite."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app + HTTP client
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app(test_settings: Settings) -> FastAPI:
    """
    Return a FastAPI app instance with test overrides applied.

    Overrides:
    - get_settings → returns test_settings
    - get_session  → returns the in-memory db_session
    """
    from api.main import create_app
    from api.deps import get_settings as dep_settings

    application = create_app()
    application.dependency_overrides[dep_settings] = lambda: test_settings
    return application


@pytest_asyncio.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Yield an async HTTP test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def override_db_dependency(app: FastAPI, db_session: AsyncSession) -> None:
    """Override FastAPI get_session dependency with the in-memory test session."""
    from api.deps import get_session
    app.dependency_overrides[get_session] = lambda: db_session
