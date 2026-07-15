"""Resilience patterns including async retries and error policies."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

async def retry_async[T](
    func: Callable[[], Coroutine[Any, Any, T]],
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> T:
    """
    Execute an async function with exponential backoff retry.
    """
    delay = initial_delay
    for attempt in range(retries):
        try:
            return await func()
        except exceptions as e:
            if attempt == retries - 1:
                logger.error(f"Function call failed after {retries} attempts: {e}")
                raise
            logger.warning(
                f"Attempt {attempt + 1} failed with error: {e}. Retrying in {delay} seconds..."
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor

    # Fallback to satisfy type checker, should not be reached due to raising in loop
    raise RuntimeError("Retry loop completed without returning or raising.")
