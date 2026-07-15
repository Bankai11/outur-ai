"""
SQLAlchemy declarative base and reusable mixins.

All ORM models in Outur AI should inherit from ``Base`` (for table mapping)
and optionally from ``TimestampMixin`` for audit timestamps.

Example
-------
::

    from core.database.base import Base, TimestampMixin

    class Company(Base, TimestampMixin):
        __tablename__ = "companies"

        id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
        name: Mapped[str] = mapped_column(String(255), nullable=False)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    All ORM models must inherit from this class so that Alembic can
    auto-generate migrations by inspecting ``Base.metadata``.
    """

    # SQLAlchemy 2.x type annotation map — extend as needed.
    type_annotation_map: dict = {}  # type: ignore[type-arg]


class TimestampMixin:
    """
    Mixin that adds ``created_at`` and ``updated_at`` columns to any model.

    Both columns are managed automatically by the database server:
    - ``created_at`` is set once on INSERT.
    - ``updated_at`` is refreshed on every UPDATE via ``onupdate``.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp when the record was first created (UTC).",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp of the last update to this record (UTC).",
    )


class UUIDMixin:
    """
    Mixin that provides a UUID v4 primary key column named ``id``.

    Uses Python-side default generation so the ID is available immediately
    after object construction — before the INSERT flush.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        doc="Universally unique identifier (UUID v4).",
    )
