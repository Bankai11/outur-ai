"""
Alembic migration environment.

This module is executed by Alembic for all migration commands
(``alembic upgrade``, ``alembic revision --autogenerate``, etc.).

Key responsibilities
--------------------
1. Load the database URL from application settings (not from alembic.ini)
   so credentials are always read from environment variables.
2. Import all ORM models so Alembic can detect schema changes automatically
   when running ``alembic revision --autogenerate``.
3. Support both sync (offline) and async (online) migration modes.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Load application settings ──────────────────────────────────────────────
# Import settings BEFORE importing models so the DB URL is available.
from core.config import get_settings

settings = get_settings()

# ── Import all models so Alembic sees them in Base.metadata ───────────────
# Add new model imports here as they are created.
from core.database.base import Base  # noqa: F401
import core.models  # noqa: F401 — triggers all model imports

# ── Alembic Config object ─────────────────────────────────────────────────
config = context.config

# Set the database URL programmatically from settings
# This overrides any sqlalchemy.url in alembic.ini
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configure Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object for autogenerate support
target_metadata = Base.metadata


# ─────────────────────────────────────────────────────────────────────────────
# Offline migrations (--sql flag — generates SQL without DB connection)
# ─────────────────────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with a URL only (no engine connection).
    Useful for generating raw SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,                  # Detect column type changes
        compare_server_default=True,        # Detect server default changes
    )
    with context.begin_transaction():
        context.run_migrations()


# ─────────────────────────────────────────────────────────────────────────────
# Online migrations (default — connects to real database)
# ─────────────────────────────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within an active database connection."""
    import alembic.ddl.sqlite
    original_sqlite_alter_column = alembic.ddl.sqlite.SQLiteImpl.alter_column

    if connection.dialect.name == "sqlite":
        # SQLite does not support direct ALTER COLUMN operations. We bypass them in testing.
        alembic.ddl.sqlite.SQLiteImpl.alter_column = lambda *args, **kwargs: None

    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    finally:
        alembic.ddl.sqlite.SQLiteImpl.alter_column = original_sqlite_alter_column


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,            # No pooling during migrations
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online async migrations."""
    asyncio.run(run_async_migrations())


# ── Dispatch ──────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
