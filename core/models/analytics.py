"""Analytics models for event tracking and campaign performance."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, Integer, Float, JSON, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel


class EmailEvent(AbstractModel):
    """Canonical event mapped to our internal schema."""
    __tablename__ = "email_events"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. opened, clicked, bounced
    occurred_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True) # IPs, user agents, link URLs


class ProviderEvent(AbstractModel):
    """Raw, unparsed webhook payload for audit and replayability."""
    __tablename__ = "provider_events"

    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventAudit(AbstractModel):
    """Ledger of processed events for deduplication and idempotency."""
    __tablename__ = "event_audits"

    event_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    processed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    provider_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_events.id", ondelete="SET NULL"), nullable=True
    )


class CampaignMetrics(AbstractModel):
    """Aggregated, real-time metrics for a campaign."""
    __tablename__ = "campaign_metrics"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0)
    total_bounced: Mapped[int] = mapped_column(Integer, default=0)
    total_deferred: Mapped[int] = mapped_column(Integer, default=0)
    
    total_opened: Mapped[int] = mapped_column(Integer, default=0)
    total_clicked: Mapped[int] = mapped_column(Integer, default=0)
    total_replied: Mapped[int] = mapped_column(Integer, default=0)
    total_meetings_booked: Mapped[int] = mapped_column(Integer, default=0)
    total_unsubscribed: Mapped[int] = mapped_column(Integer, default=0)
    total_spam_complaints: Mapped[int] = mapped_column(Integer, default=0)
    
    health_score: Mapped[float] = mapped_column(Float, default=100.0)


class RecipientActivity(AbstractModel):
    """Timeline of actions performed by a specific recipient."""
    __tablename__ = "recipient_activities"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    first_opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    
    first_clicked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_clicked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    
    replied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AnalyticsSnapshot(AbstractModel):
    """Time-series rollups for charting."""
    __tablename__ = "analytics_snapshots"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True) # Truncated to day or hour
    
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, default=0.0)
