"""Database package — public surface for engine, session, and base classes."""

from core.database.base import Base, TimestampMixin, UUIDMixin
from core.database.engine import (
    async_session_factory,
    check_db_connection,
    engine,
    get_async_session,
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # Engine & sessions
    "engine",
    "async_session_factory",
    "get_async_session",
    "check_db_connection",
]
