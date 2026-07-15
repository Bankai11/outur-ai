"""
SQLAlchemy async engine and session factory.

Usage
-----
In FastAPI dependency injection::

    from core.database import get_async_session

    async def endpoint(session: AsyncSession = Depends(get_async_session)):
        ...

Standalone usage (e.g., scripts)::

    from core.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(MyModel))
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
kwargs: dict[str, Any] = {
    "echo": settings.is_development,
    "pool_pre_ping": True,
}

if settings.database_url.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool
    kwargs["poolclass"] = StaticPool
    kwargs["connect_args"] = {"check_same_thread": False}
else:
    kwargs["pool_size"] = settings.database_pool_size
    kwargs["max_overflow"] = settings.database_max_overflow
    kwargs["pool_timeout"] = settings.database_pool_timeout

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    **kwargs
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,                 # Safer for async — avoids lazy-load errors
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a managed async database session.

    Commits on success, rolls back on exception, always closes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Health-check helper: returns True if the database is reachable.

    Used by the /health endpoint.
    """
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
