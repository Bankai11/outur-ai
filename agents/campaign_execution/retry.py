"""Retry logic and backoff calculation for campaign execution."""

import random

def calculate_backoff(attempt: int, base_delay: int = 60, max_delay: int = 3600) -> int:
    """
    Calculate exponential backoff with jitter.
    
    Args:
        attempt: The current attempt number (0-indexed).
        base_delay: The base delay in seconds.
        max_delay: The maximum delay in seconds.
        
    Returns:
        The delay in seconds before the next attempt.
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = base_delay * (2 ** attempt)
    
    # Add jitter (±20%)
    jitter = delay * 0.2
    actual_delay = delay + random.uniform(-jitter, jitter)
    
    return int(min(actual_delay, max_delay))
