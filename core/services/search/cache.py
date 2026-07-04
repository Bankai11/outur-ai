"""SQLite implementation of the Search Cache."""

import json
import time
import aiosqlite
from typing import Any
from pathlib import Path

from core.logger import get_logger
from core.services.search.base import BaseCache

log = get_logger(__name__)


class SQLiteCache(BaseCache):
    """
    SQLite-backed cache for search provider responses.
    This fulfills the requirement for a robust default BaseCache abstraction.
    """
    def __init__(self, db_path: str = "search_cache.sqlite"):
        self.db_path = Path(db_path)
        self._initialized = False

    async def _init_db(self):
        """Create the cache table if it doesn't exist."""
        if self._initialized:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)")
            await db.commit()
            self._initialized = True

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a valid value from the cache."""
        await self._init_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", 
                (key,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    value_json, expires_at = row
                    
                    # Check expiration
                    if expires_at and time.time() > expires_at:
                        # Expired, clean it up
                        await db.execute("DELETE FROM cache WHERE key = ?", (key,))
                        await db.commit()
                        return None
                        
                    try:
                        return json.loads(value_json)
                    except json.JSONDecodeError:
                        log.error(f"Failed to decode cached value for key {key}")
                        return None
                        
        return None

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store a value in the cache."""
        await self._init_db()
        
        expires_at = time.time() + ttl if ttl else None
        value_json = json.dumps(value)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, value_json, expires_at)
            )
            await db.commit()
            
    async def cleanup(self):
        """Remove all expired entries from the cache."""
        await self._init_db()
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache WHERE expires_at < ?", (now,))
            await db.commit()
