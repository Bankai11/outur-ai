"""Pydantic schemas for the analytics subsystem."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StandardEventPayload(BaseModel):
    """The normalized event structure parsed from any provider webhook."""
    provider_name: str
    provider_message_id: str
    event_type: str # e.g. "delivered", "opened", "clicked", "bounced", "spam", "deferred"
    occurred_at: datetime
    raw_payload: dict[str, Any]
    event_metadata: dict[str, Any] = Field(default_factory=dict)

class CampaignStats(BaseModel):
    """API response model for campaign statistics."""
    campaign_id: UUID
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_deferred: int
    total_opened: int
    total_clicked: int
    total_replied: int
    total_meetings_booked: int
    total_unsubscribed: int
    total_spam_complaints: int
    health_score: float
    delivery_rate: float
    open_rate: float
    click_rate: float
    reply_rate: float
