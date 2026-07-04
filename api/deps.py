"""
FastAPI dependency injection providers.

All reusable dependencies live here so they can be swapped in tests
via ``app.dependency_overrides``.

Usage
-----
::

    from api.deps import get_session, get_settings

    @router.get("/example")
    async def example(
        session: AsyncSession = Depends(get_session),
        settings: Settings = Depends(get_settings),
    ):
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.config import get_settings as _get_settings
from core.database import get_async_session


# ── Database session ───────────────────────────────────────────────────────

async def get_session() -> AsyncSession:  # type: ignore[return]
    """
    Yield a managed async database session.

    Wraps ``core.database.get_async_session`` so that tests can override
    this dependency independently of the database engine.
    """
    async for session in get_async_session():
        yield session


# ── Settings ───────────────────────────────────────────────────────────────

def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Wraps the core ``get_settings`` so routes declare a clean
    FastAPI-compatible dependency signature.
    """
    return _get_settings()


# ── Typed aliases (use these in route signatures for clean type hints) ─────

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
