"""Analytics Service for external components to interact with."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.analytics.aggregator import MetricsAggregator
from agents.analytics.models import CampaignStats
from agents.analytics.processor import EventProcessor
from core.models.analytics import CampaignMetrics, ProviderEvent


class AnalyticsService:
    """Facade for the Analytics Subsystem."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.processor = EventProcessor(db)
        self.aggregator = MetricsAggregator(db)

    async def record_raw_webhook(self, provider: str, payload: dict) -> UUID:
        """Store a raw webhook payload for processing."""
        event = ProviderEvent(
            provider_name=provider,
            raw_payload=payload,
            received_at=datetime.now(UTC),
            processed=False
        )
        self.db.add(event)
        await self.db.commit()
        return event.id

    async def get_campaign_stats(self, campaign_id: UUID) -> CampaignStats:
        """Get the current metrics for a campaign."""
        result = await self.db.execute(
            select(CampaignMetrics).where(CampaignMetrics.campaign_id == campaign_id)
        )
        metrics = result.scalars().first()

        if not metrics:
            return CampaignStats(
                campaign_id=campaign_id,
                total_sent=0, total_delivered=0, total_bounced=0, total_deferred=0,
                total_opened=0, total_clicked=0, total_replied=0, total_meetings_booked=0,
                total_unsubscribed=0, total_spam_complaints=0,
                health_score=0.0, delivery_rate=0.0, open_rate=0.0, click_rate=0.0, reply_rate=0.0
            )

        return CampaignStats(
            campaign_id=metrics.campaign_id,
            total_sent=metrics.total_sent,
            total_delivered=metrics.total_delivered,
            total_bounced=metrics.total_bounced,
            total_deferred=metrics.total_deferred,
            total_opened=metrics.total_opened,
            total_clicked=metrics.total_clicked,
            total_replied=metrics.total_replied,
            total_meetings_booked=metrics.total_meetings_booked,
            total_unsubscribed=metrics.total_unsubscribed,
            total_spam_complaints=metrics.total_spam_complaints,
            health_score=metrics.health_score,
            delivery_rate=0.0, # These could be fetched or re-calculated on the fly
            open_rate=0.0,
            click_rate=0.0,
            reply_rate=0.0
        )
