"""
Request / response logging middleware.

Logs every inbound request and its corresponding response with:
- Method, path, query string
- Response status code and latency (ms)
- A unique ``request_id`` (UUID) injected into structlog context for the
  entire request lifecycle — any log.* call inside a handler automatically
  includes it.

The middleware uses ``structlog.contextvars`` so the request_id flows
transparently into all structured log statements without passing it manually.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that emits structured access logs for every HTTP request.

    Timing is measured in milliseconds. The ``request_id`` is a UUID4 that is:
    - Bound to structlog's contextvars (available to all log calls in the request)
    - Returned in the ``X-Request-ID`` response header for client correlation
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = str(uuid.uuid4())

        # Bind request_id so all downstream log calls include it automatically
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()

        log.info(
            "Request received",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) or None,
            client=request.client.host if request.client else None,
        )

        try:
            response: Response = await call_next(request)  # type: ignore[operator]
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log.error(
                "Request failed with unhandled exception",
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
                exc_info=exc,
            )
            raise

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        log.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        # Surface request_id to the client for tracing
        response.headers["X-Request-ID"] = request_id

        return response
