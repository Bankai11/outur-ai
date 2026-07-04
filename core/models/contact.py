"""Contact model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AbstractModel


class Contact(AbstractModel):
    """
    ORM Model representing a contact/lead discovered for a company.
    """

    __tablename__ = "contacts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    # Evidence & Verification Fields
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mx_valid: Mapped[bool | None] = mapped_column(nullable=True)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="contacts")
