"""
Structured logging configuration using ``structlog``.

Features
--------
- JSON output in production / staging (machine-parseable)
- Human-readable coloured console output in development
- Automatic request-id context propagation
- Standard library ``logging`` integration (third-party libs log through here too)
- Log level controlled by ``settings.log_level``

Usage
-----
Import the logger anywhere in the codebase::

    from core.logger import get_logger

    log = get_logger(__name__)
    log.info("Company found", company_id=str(company.id), source="apollo")

The ``__name__`` convention keeps log output clearly attributed to its module.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from core.config import LogFormat, get_settings


def _add_app_context(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Structlog processor: inject static app-level context into every log record.

    This adds ``app`` and ``env`` fields so log aggregators can filter by service.
    """
    settings = get_settings()
    event_dict.setdefault("app", settings.app_name)
    event_dict.setdefault("env", settings.app_env.value)
    return event_dict


def _drop_color_message_key(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Structlog processor: remove the ``color_message`` key added by uvicorn.

    Uvicorn injects this key for its own colourised output; we don't want it
    polluting our structured JSON logs.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure both ``structlog`` and the standard-library ``logging`` module.

    Call this **once** at application startup (in ``api/main.py`` lifespan).
    Subsequent calls are safe (idempotent) but unnecessary.
    """
    settings = get_settings()
    log_level = logging.getLevelName(settings.log_level.value)

    # ── Shared processors applied to every log record ──────────────────────
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,        # Async-safe context (request-id etc.)
        structlog.stdlib.add_logger_name,               # module name
        structlog.stdlib.add_log_level,                 # level string
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),    # ISO-8601 timestamp
        structlog.processors.StackInfoRenderer(),
        _add_app_context,
        _drop_color_message_key,
    ]

    # ── Format-specific renderer ────────────────────────────────────────────
    if settings.log_format == LogFormat.JSON:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # ── Configure structlog ─────────────────────────────────────────────────
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ── Standard library root logger → structlog ────────────────────────────
    formatter = structlog.stdlib.ProcessorFormatter(
        # These run only on records coming from stdlib logging (e.g. sqlalchemy, uvicorn)
        foreign_pre_chain=shared_processors,
        processor=renderer,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers in production
    if not settings.is_development:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structlog logger bound to the given module name.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.

    Returns
    -------
    structlog.stdlib.BoundLogger
        A bound logger instance ready for structured logging.
    """
    return structlog.get_logger(name)
