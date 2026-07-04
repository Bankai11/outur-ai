"""
Typed application exception hierarchy for Outur AI.

Design principles
-----------------
1. Every exception carries ``status_code``, ``error_code``, and ``detail``
   so FastAPI exception handlers can produce consistent HTTP responses.
2. Exceptions are organised in a two-level hierarchy:
   ``OUTURAIError`` → domain-specific subclasses.
3. ``error_code`` is a machine-readable snake_case string for API consumers.

Usage
-----
Raise from business logic::

    from core.utils.exceptions import NotFoundError
    raise NotFoundError(resource="Company", identifier=company_id)

Handle in FastAPI::

    from fastapi import Request
    from fastapi.responses import JSONResponse
    from core.utils.exceptions import OUTURAIError

    @app.exception_handler(OUTURAIError)
    async def outur_error_handler(request: Request, exc: OUTURAIError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
"""

from __future__ import annotations

from typing import Any


class OUTURAIError(Exception):
    """
    Base class for all application-level exceptions.

    Attributes
    ----------
    status_code:
        HTTP status code to return to the API client.
    error_code:
        Machine-readable identifier (e.g. ``"not_found"``, ``"validation_error"``).
    detail:
        Human-readable description of the error.
    context:
        Optional dict of additional structured context (logged, not returned to client).
    """

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        detail: str = "An unexpected error occurred.",
        context: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail
        self.context = context or {}
        super().__init__(detail)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict for HTTP responses."""
        return {
            "error": self.error_code,
            "detail": self.detail,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(error_code={self.error_code!r}, detail={self.detail!r})"


# ── 4xx Client Errors ──────────────────────────────────────────────────────

class ValidationError(OUTURAIError):
    """Raised when input data fails business-rule validation (422)."""

    status_code = 422
    error_code = "validation_error"

    def __init__(self, detail: str = "Validation failed.", field: str | None = None) -> None:
        self.field = field
        context = {"field": field} if field else {}
        super().__init__(detail=detail, context=context)


class NotFoundError(OUTURAIError):
    """Raised when a requested resource does not exist (404)."""

    status_code = 404
    error_code = "not_found"

    def __init__(self, resource: str = "Resource", identifier: Any = None) -> None:
        detail = f"{resource} not found."
        if identifier is not None:
            detail = f"{resource} with id '{identifier}' not found."
        super().__init__(detail=detail, context={"resource": resource, "id": str(identifier)})


class ConflictError(OUTURAIError):
    """Raised when an action conflicts with existing state (409)."""

    status_code = 409
    error_code = "conflict"

    def __init__(self, detail: str = "Resource conflict.") -> None:
        super().__init__(detail=detail)


class UnauthorizedError(OUTURAIError):
    """Raised when a request lacks valid authentication (401)."""

    status_code = 401
    error_code = "unauthorized"

    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(detail=detail)


class ForbiddenError(OUTURAIError):
    """Raised when an authenticated user lacks permission (403)."""

    status_code = 403
    error_code = "forbidden"

    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(detail=detail)


class RateLimitError(OUTURAIError):
    """Raised when an external or internal rate limit is exceeded (429)."""

    status_code = 429
    error_code = "rate_limit_exceeded"

    def __init__(self, detail: str = "Rate limit exceeded. Please retry later.") -> None:
        super().__init__(detail=detail)


# ── 5xx Server Errors ──────────────────────────────────────────────────────

class DatabaseError(OUTURAIError):
    """Raised when a database operation fails unexpectedly (500)."""

    status_code = 500
    error_code = "database_error"

    def __init__(self, detail: str = "A database error occurred.") -> None:
        super().__init__(detail=detail)


class ExternalServiceError(OUTURAIError):
    """Raised when a third-party API call fails (502)."""

    status_code = 502
    error_code = "external_service_error"

    def __init__(self, service: str, detail: str = "External service unavailable.") -> None:
        super().__init__(detail=detail, context={"service": service})


class ConfigurationError(OUTURAIError):
    """Raised when required configuration is missing or invalid (500)."""

    status_code = 500
    error_code = "configuration_error"

    def __init__(self, detail: str = "Server configuration error.") -> None:
        super().__init__(detail=detail)
