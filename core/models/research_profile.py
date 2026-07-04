"""ResearchProfile database model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Integer, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AbstractModel

if TYPE_CHECKING:
    from core.models.company import Company


class ResearchProfile(AbstractModel):
    """
    Structured research profile for a company to support outreach personalization.
    """

    __tablename__ = "research_profiles"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Core structured intelligence
    employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_estimated: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    technologies_used: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    competitors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    hr_maturity: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Evidence-backed signals
    recent_news: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    hiring_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    growth_indicators: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    public_pain_points: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    ai_adoption_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    
    # Scores & Decisions
    best_contact: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    why_now_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Raw enrichment evidence storage
    raw_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    
    # Granular confidence scores
    llm_confidence: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    data_quality: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    freshness_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    # Naive DateTime matching core models timezone naive style
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="research_profile")
