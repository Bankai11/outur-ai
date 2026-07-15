"""Company model definition."""

from __future__ import annotations

from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AbstractModel


class Company(AbstractModel):
    """
    ORM Model representing a company discovered by the system.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    careers_page: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)

    # Scoring fields
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(10), nullable=True)
    score_signals: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    enrichment_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    contacts: Mapped[list[Contact]] = relationship(
        "Contact",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    sales_intelligence_profile: Mapped[SalesIntelligenceProfile | None] = relationship(
        "SalesIntelligenceProfile",
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
