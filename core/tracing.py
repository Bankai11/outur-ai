"""Execution tracing and timeline logging context managers."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog

log = structlog.get_logger(__name__)

@contextmanager
def trace_execution(
    name: str,
    campaign_id: str | None = None,
    contact_id: str | None = None,
    extra: dict[str, Any] | None = None
) -> Generator[None, None, None]:
    """
    Context manager to track execution latencies and log structural timeline steps.
    Logs structured tracing variables automatically to support campaign end-to-end tracing.
    """
    start_time = time.perf_counter()
    extra_fields = extra or {}

    # Extract correlation id if bound in contextvars
    ctx_vars = structlog.contextvars.get_contextvars()
    correlation_id = ctx_vars.get("correlation_id")

    log.debug(
        f"Trace started: {name}",
        step_name=name,
        campaign_id=campaign_id,
        contact_id=contact_id,
        correlation_id=correlation_id,
        **extra_fields
    )

    try:
        yield
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log.error(
            f"Trace failed: {name}",
            step_name=name,
            campaign_id=campaign_id,
            contact_id=contact_id,
            correlation_id=correlation_id,
            elapsed_ms=elapsed_ms,
            error=str(exc),
            **extra_fields
        )
        raise

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    log.info(
        f"Trace completed: {name}",
        step_name=name,
        campaign_id=campaign_id,
        contact_id=contact_id,
        correlation_id=correlation_id,
        elapsed_ms=elapsed_ms,
        **extra_fields
    )
