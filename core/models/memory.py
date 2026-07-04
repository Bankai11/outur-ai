"""Memory models for entity knowledge tracking."""

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AbstractModel


class CompanyMemory(AbstractModel):
    """
    Accumulated knowledge about a company across all campaigns and interactions.
    """
    __tablename__ = "company_memories"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Evolving structured knowledge
    known_objections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    past_engagement_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    buying_intent_score: Mapped[int] = mapped_column(default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    company: Mapped["Company"] = relationship("Company", backref="memory")


class ContactMemory(AbstractModel):
    """
    Accumulated knowledge about a specific contact.
    """
    __tablename__ = "contact_memories"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Evolving structured knowledge
    communication_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    past_replies: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    contact: Mapped["Contact"] = relationship("Contact", backref="memory")


class CampaignMemory(AbstractModel):
    """
    Accumulated knowledge and learnings from a specific campaign.
    """
    __tablename__ = "campaign_memories"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Campaign learnings
    successful_angles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failed_angles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    audience_insights: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", backref="memory")


class OrganizationMemory(AbstractModel):
    """
    The highest level of memory. Tracks overall organizational knowledge,
    brand voice learnings, and high-level strategy over time.
    """
    __tablename__ = "organization_memories"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    core_value_props: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    brand_voice_guidelines: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    global_do_not_contact: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class ConversationMemory(AbstractModel):
    """
    Tracks the full back-and-forth context of an ongoing interaction with a contact.
    """
    __tablename__ = "conversation_memories"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    
    thread_history: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    current_intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_action_due: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    contact: Mapped["Contact"] = relationship("Contact", backref="conversation")


class IndustryMemory(AbstractModel):
    """
    Tracks macro-level insights for a specific industry (e.g. Healthcare, B2B SaaS).
    """
    __tablename__ = "industry_memories"

    industry_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    common_pain_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    buying_cycles: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    average_wait_days: Mapped[int] = mapped_column(default=3, nullable=False)


class MarketMemory(AbstractModel):
    """
    Tracks macro-level insights for a specific market segment or geography.
    """
    __tablename__ = "market_memories"

    segment_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    trends: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    competitor_landscape: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
