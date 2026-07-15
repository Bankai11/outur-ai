"""Database models for campaign execution."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel


class CampaignRun(AbstractModel):
    """
    A specific execution run of a campaign.
    """
    __tablename__ = "campaign_runs"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_drafts: Mapped[int] = mapped_column(Integer, default=0)
    successful_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0)


class CampaignDelivery(AbstractModel):
    """
    State of delivery for a specific outreach draft.
    """
    __tablename__ = "campaign_deliveries"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outreach_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(nullable=True)


class DeliveryAttempt(AbstractModel):
    """
    An individual attempt to send an email (for retry tracking).
    """
    __tablename__ = "delivery_attempts"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


class DeliveryEvent(AbstractModel):
    """
    Webhook events or callbacks related to a delivery (opened, clicked, bounced).
    """
    __tablename__ = "delivery_events"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
