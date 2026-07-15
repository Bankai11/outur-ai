"""Database models for the Autonomous Decision Engine."""

from __future__ import annotations
from typing import Any
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, JSON, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel

class CampaignState(AbstractModel):
    """
    Tracks campaign-level states with strict transition auditing.
    """
    __tablename__ = "campaign_states"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    # e.g., CREATED, RUNNING, COMPLETED, FAILED, CANCELLED
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="CREATED", index=True)
    transitioned_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    
    # Audit trail of transitions: list of dicts with {"from": str, "to": str, "at": str, "reason": str}
    transition_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class RecipientLifecycle(AbstractModel):
    """
    Tracks the lifecycle state of a contact within a specific campaign.
    """
    __tablename__ = "recipient_lifecycles"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # States: CREATED, DISCOVERING, ENRICHING, SCORING, RESEARCHING, GENERATING, READY, QUEUED,
    #         RUNNING, WAITING, FOLLOWUP_PENDING, FOLLOWUP_SENT, REPLIED, MEETING_BOOKED, COMPLETED, FAILED, CANCELLED
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="CREATED", index=True)
    state_entered_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    next_evaluation_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class DecisionHistory(AbstractModel):
    """
    Audit log of all decisions made by the engine for a contact in a campaign.
    """
    __tablename__ = "decision_history"
    
    recipient_lifecycle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipient_lifecycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Snapshot of inputs at decision time
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Struct of DecisionResult
    decision: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    
    # Execution tracing
    execution_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    execution_outcome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    
    # Versions for reproducibility
    llm_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
