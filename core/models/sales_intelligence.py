"""SalesIntelligenceProfile database model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Integer, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AbstractModel

if TYPE_CHECKING:
    from core.models.company import Company


class SalesIntelligenceProfile(AbstractModel):
    """
    Structured sales intelligence profile for a company to support outbound outreach.
    """

    __tablename__ = "sales_intelligence_profiles"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Business Context
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_customers: Mapped[str | None] = mapped_column(Text, nullable=True)
    products_services: Mapped[str | None] = mapped_column(Text, nullable=True)
    growth_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategic_initiatives: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitive_landscape: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_differentiators: Mapped[str | None] = mapped_column(Text, nullable=True)
    recent_news: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    recent_funding: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    technology_stack: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Signals
    hiring_activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    hiring_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    buying_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    digital_transformation_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    
    # Sales Intelligence Specifics
    pain_points: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    product_value_mapping: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    potential_decision_makers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_opportunity_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Outreach Intelligence
    outreach_intelligence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    primary_trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_playbook: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata
    confidence_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    supporting_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Naive DateTime matching core models timezone naive style
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="sales_intelligence_profile")
