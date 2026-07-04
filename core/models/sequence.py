"""Models for multi-step outreach sequences."""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AbstractModel


class OutreachSequence(AbstractModel):
    """
    A sequence of outreach steps for a specific contact in a campaign.
    Replaces the single OutreachDraft concept.
    """
    __tablename__ = "outreach_sequences"

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
    
    # State tracking
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False) # draft, active, paused, completed, bounced, replied
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    steps: Mapped[list["SequenceStep"]] = relationship(
        "SequenceStep", back_populates="sequence", cascade="all, delete-orphan", order_by="SequenceStep.step_order"
    )


class SequenceStep(AbstractModel):
    """
    An individual step within a sequence (e.g. Email 1, LinkedIn Message, Wait).
    """
    __tablename__ = "sequence_steps"

    sequence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outreach_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False) # email, linkedin, wait
    
    # Content (if channel is email/linkedin)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Wait properties (if channel is wait)
    wait_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Execution state
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False) # pending, scheduled, completed, failed
    scheduled_for: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    executed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    # External tracking
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    sequence: Mapped["OutreachSequence"] = relationship("OutreachSequence", back_populates="steps")
