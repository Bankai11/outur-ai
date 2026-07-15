"""Pydantic models for Decision Engine data structures."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DecisionResult(BaseModel):
    """Structured decision output produced by the decision engine."""

    decision_id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    recipient_id: UUID  # Maps to contact_id
    recommended_action: str  # WAIT, SEND_FOLLOWUP, CHANGE_SUBJECT, etc.
    reason: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    priority: str = "medium"  # low, medium, high
    scheduled_at: datetime | None = None
    rule_triggered: str | None = None
    llm_used: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationContext(BaseModel):
    """Aggregated context containing all information required for making a decision."""

    campaign_id: UUID
    contact_id: UUID
    current_state: str
    opportunity_score: float = 50.0
    campaign_metrics: dict[str, Any] = Field(default_factory=dict)
    recipient_activity: dict[str, Any] = Field(default_factory=dict)
    email_events: list[dict[str, Any]] = Field(default_factory=list)
    previous_emails_count: int = 0
    days_since_last_interaction: float = 0.0
    buying_signals: dict[str, Any] = Field(default_factory=dict)
    company_context: dict[str, Any] = Field(default_factory=dict)
