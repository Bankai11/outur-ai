"""
Database seeding script — development & staging only.

Seeds the database with sample data to make local development easier.
DO NOT run this in production.

Usage
-----
::

    uv run python scripts/seed_db.py

Or via the dev setup script::

    scripts/setup_dev.ps1
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings
from core.logger import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

settings = get_settings()


async def seed() -> None:
    """Run all seed operations."""
    if settings.is_production:
        log.error("Refusing to seed production database. Exiting.")
        sys.exit(1)

    log.info("Starting database seed", env=settings.app_env.value)

    # TODO: Add seed operations here as models are created.
    # Example:
    #   from core.database import async_session_factory
    #   from core.models.company import Company
    #   async with async_session_factory() as session:
    #       session.add(Company(name="Acme Corp", domain="acme.com"))
    #       await session.commit()

    log.info("Database seeding complete — no data to seed yet (stub)")


if __name__ == "__main__":
    asyncio.run(seed())
