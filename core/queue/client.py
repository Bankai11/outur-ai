"""ARQ Redis connection pool client for enqueuing jobs."""

from arq import create_pool
from arq.connections import RedisSettings
from urllib.parse import urlparse

from core.config.settings import get_settings
from core.logger import get_logger

log = get_logger(__name__)

# Global connection pool instance
_redis_pool = None


def get_redis_settings() -> RedisSettings:
    """Parse the redis_url into ARQ's RedisSettings."""
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/")) if parsed.path else 0,
        username=parsed.username,
        password=parsed.password,
    )


async def init_redis_pool():
    """Initialize the global Redis connection pool for ARQ."""
    global _redis_pool
    if _redis_pool is None:
        log.info("Initializing ARQ Redis pool...")
        redis_settings = get_redis_settings()
        _redis_pool = await create_pool(redis_settings)
    return _redis_pool


async def get_redis_pool():
    """Get the active ARQ Redis connection pool."""
    if _redis_pool is None:
        return await init_redis_pool()
    return _redis_pool


async def close_redis_pool():
    """Close the global Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        log.info("Closing ARQ Redis pool...")
        await _redis_pool.close()
        _redis_pool = None
