"""Utils package — shared utilities."""

from core.utils.exceptions import (
    ConfigurationError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    OUTURAIError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)
from core.utils.pagination import (
    CursorPage,
    CursorParams,
    OffsetParams,
    PaginatedResponse,
    decode_cursor,
    encode_cursor,
)

__all__ = [
    # Exceptions
    "OUTURAIError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "RateLimitError",
    "DatabaseError",
    "ExternalServiceError",
    "ConfigurationError",
    # Pagination
    "OffsetParams",
    "PaginatedResponse",
    "CursorParams",
    "CursorPage",
    "encode_cursor",
    "decode_cursor",
]
