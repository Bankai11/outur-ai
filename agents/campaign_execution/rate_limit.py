"""Rate limiting logic for campaign execution."""

import time
from redis.asyncio import Redis

class RateLimiter:
    """Redis-backed rate limiter for delivery providers."""
    
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_rate_limit(self, provider_id: str, limit_per_minute: int) -> bool:
        """
        Check if the provider has exceeded its rate limit.
        Uses a simple fixed window based on the current minute.
        
        Args:
            provider_id: Unique identifier for the provider (e.g., domain or account ID).
            limit_per_minute: The maximum number of requests allowed per minute.
            
        Returns:
            True if the request is allowed, False if rate limited.
        """
        current_minute = int(time.time() // 60)
        key = f"rate_limit:{provider_id}:{current_minute}"
        
        # Increment the counter
        current_count = await self.redis.incr(key)
        
        # If this is the first request in this minute, set an expiration
        if current_count == 1:
            await self.redis.expire(key, 60)
            
        return current_count <= limit_per_minute

    async def wait_if_needed(self, provider_id: str, limit_per_minute: int) -> None:
        """
        Check rate limit and sleep if exceeded.
        """
        import asyncio
        while not await self.check_rate_limit(provider_id, limit_per_minute):
            # Wait for the next minute boundary (rough approximation)
            await asyncio.sleep(1.0)
