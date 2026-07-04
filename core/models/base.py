"""
Abstract base model for all SQLAlchemy ORM entities.

``AbstractModel`` combines ``Base``, ``UUIDMixin``, and ``TimestampMixin``
into a single convenient base class. Use it for all domain models unless
you have a specific reason not to include UUID PKs or timestamps.

Example
-------
::

    from core.models.base import AbstractModel
    from sqlalchemy.orm import Mapped, mapped_column
    from sqlalchemy import String

    class Company(AbstractModel):
        __tablename__ = "companies"

        name: Mapped[str] = mapped_column(String(255))
        domain: Mapped[str | None] = mapped_column(String(255))
"""

from __future__ import annotations

from core.database.base import Base, TimestampMixin, UUIDMixin


class AbstractModel(UUIDMixin, TimestampMixin, Base):
    """
    Concrete-ready abstract base that all domain models should inherit from.

    Provides:
    - ``id`` — UUID v4 primary key
    - ``created_at`` — server-set creation timestamp (UTC)
    - ``updated_at`` — server-set update timestamp (UTC, auto-refreshed)

    Mark as abstract in SQLAlchemy by using ``__abstract__ = True`` only when
    you want to create your own intermediate base without a corresponding table.
    """

    __abstract__ = True

    def __repr__(self) -> str:
        """Default repr includes class name and primary key."""
        return f"<{self.__class__.__name__} id={self.id}>"
