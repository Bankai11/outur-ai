"""OutreachDraft database model."""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel


class OutreachDraft(AbstractModel):
    """
    Personalized outreach draft cold email generated for a specific contact in a campaign.
    """

    __tablename__ = "outreach_drafts"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    
    # QA and Review
    approval_status: Mapped[str] = mapped_column(String(50), default="pending_qa", nullable=False)
    qa_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qa_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Email Delivery Tracking
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    # AI Personalization Evidence
    pain_signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    primary_trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    playbook_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Reply Tracking
    reply_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    reply_received_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reply_classification: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
