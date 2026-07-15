"""Async cache utility for LLM calls with BaseCache abstraction."""

from __future__ import annotations

import sqlite3
import json
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

class BaseCache(ABC):
    """Abstract base class for caching mechanisms."""
    
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value by key. Return None if not found or expired."""
        ...
        
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        """Store a value by key with an optional TTL in seconds."""
        ...


class SQLiteCache(BaseCache):
    """SQLite-backed async cache implementation."""
    
    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            try:
                from core.config import get_settings
                settings = get_settings()
                if settings.app_env == "testing":
                    db_path = ".outur_cache_test.db"
                else:
                    db_path = ".outur_cache.db"
            except ImportError:
                db_path = ".outur_cache.db"
        self.db_path = Path(db_path)
        self._init_cache()

    def _init_cache(self) -> None:
        """Initialize the cache database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Upgrade table schema to support expires_at
            # We'll recreate if it doesn't have the column to be safe for this transition
            # Check existing columns
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT expires_at FROM llm_cache LIMIT 1")
            except sqlite3.OperationalError:
                # Need to migrate
                try:
                    conn.execute("ALTER TABLE llm_cache ADD COLUMN expires_at REAL")
                except sqlite3.OperationalError:
                    # Table might not exist yet
                    pass
                    
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_cache (
                    key TEXT PRIMARY KEY,
                    response_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at REAL
                )
                """
            )

    async def get(self, key: str) -> Any | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_json, expires_at FROM llm_cache WHERE key = ?", 
                (key,)
            )
            row = cursor.fetchone()
            
        if row:
            response_json, expires_at = row
            # Check TTL
            if expires_at and time.time() > expires_at:
                # Expired
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM llm_cache WHERE key = ?", (key,))
                return None
                
            try:
                return json.loads(response_json)
            except json.JSONDecodeError:
                return None
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        response_str = json.dumps(value)
        expires_at = time.time() + ttl_seconds
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache (key, response_json, expires_at)
                VALUES (?, ?, ?)
                """,
                (key, response_str, expires_at)
            )

# Global cache instance
_cache_instance: BaseCache | None = None

def get_cache() -> BaseCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SQLiteCache()
    return _cache_instance

def set_cache(cache: BaseCache) -> None:
    """Override the global cache instance (useful for testing)."""
    global _cache_instance
    _cache_instance = cache

def generate_cache_key(prompt: str, schema: dict[str, Any]) -> str:
    """Generate a consistent hash for a prompt and schema combination."""
    schema_str = json.dumps(schema, sort_keys=True)
    combined = f"{prompt}|{schema_str}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

# Backward compatibility functions
async def get_cached_response(prompt: str, schema: dict[str, Any]) -> Any | None:
    key = generate_cache_key(prompt, schema)
    return await get_cache().get(key)

async def set_cached_response(prompt: str, schema: dict[str, Any], response: Any, ttl_seconds: int = 86400) -> None:
    key = generate_cache_key(prompt, schema)
    await get_cache().set(key, response, ttl_seconds)
