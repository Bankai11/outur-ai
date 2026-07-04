"""
Generic pagination utilities.

Supports two pagination strategies:
- **Offset pagination** — simple page/page_size (good for small, stable datasets).
- **Cursor pagination** — token-based (good for large, append-only datasets like lead feeds).

Usage
-----
Offset::

    from core.utils.pagination import OffsetParams, PaginatedResponse
    from fastapi import Depends

    @router.get("/companies", response_model=PaginatedResponse[CompanySchema])
    async def list_companies(params: OffsetParams = Depends()):
        ...

Cursor::

    from core.utils.pagination import CursorParams, CursorPage

    @router.get("/leads", response_model=CursorPage[LeadSchema])
    async def stream_leads(params: CursorParams = Depends()):
        ...
"""

from __future__ import annotations

import base64
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Offset Pagination
# ---------------------------------------------------------------------------

class OffsetParams(BaseModel):
    """
    Query parameters for offset-based pagination.

    Inject via FastAPI ``Depends``::

        params: OffsetParams = Depends()
    """

    page: int = Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100).")

    @property
    def offset(self) -> int:
        """Calculate the SQL OFFSET from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size — matches SQLAlchemy's ``limit()`` convention."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard envelope for offset-paginated list responses.

    Fields
    ------
    items   : The page of results.
    total   : Total number of matching records in the database.
    page    : Current page number (1-indexed).
    pages   : Total number of pages.
    has_next: Whether a next page exists.
    has_prev: Whether a previous page exists.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: list[T], total: int, params: OffsetParams) -> "PaginatedResponse[T]":
        """Construct a PaginatedResponse from query results and params."""
        pages = max(1, -(-total // params.page_size))  # ceiling division
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
            has_next=params.page < pages,
            has_prev=params.page > 1,
        )


# ---------------------------------------------------------------------------
# Cursor Pagination
# ---------------------------------------------------------------------------

def encode_cursor(value: str) -> str:
    """Encode a raw cursor value to a URL-safe base64 string."""
    return base64.urlsafe_b64encode(value.encode()).decode()


def decode_cursor(token: str) -> str:
    """Decode a base64 cursor token back to its raw value."""
    return base64.urlsafe_b64decode(token.encode()).decode()


class CursorParams(BaseModel):
    """
    Query parameters for cursor-based pagination.

    The ``cursor`` is an opaque token returned by the previous response.
    Clients should treat it as a black box.
    """

    cursor: str | None = Field(default=None, description="Opaque pagination cursor from previous response.")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items to return.")


class CursorPage(BaseModel, Generic[T]):
    """
    Cursor-paginated response envelope.

    Fields
    ------
    items       : The current page of results.
    next_cursor : Cursor to pass in the next request; ``null`` means end of results.
    has_next    : Convenience flag — true when next_cursor is not null.
    """

    items: list[T]
    next_cursor: str | None = None
    has_next: bool

    @classmethod
    def create(cls, items: list[T], next_cursor: str | None) -> "CursorPage[T]":
        """Construct a CursorPage from items and the next cursor value."""
        return cls(items=items, next_cursor=next_cursor, has_next=next_cursor is not None)
