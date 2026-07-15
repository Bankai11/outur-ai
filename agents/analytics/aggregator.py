"""Aggregator for computing campaign-level metrics."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.analytics.metrics import calculate_rates
from core.models.analytics import CampaignMetrics, EmailEvent

logger = logging.getLogger(__name__)

class MetricsAggregator:
    """Aggregates individual events into campaign-level metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def aggregate_campaign(self, campaign_id: UUID) -> None:
        """Compute metrics for a campaign and update the DB."""

        # 1. Get counts for each event type
        result = await self.db.execute(
            select(
                EmailEvent.event_type,
                func.count(EmailEvent.id).label("count")
            )
            .where(EmailEvent.campaign_id == campaign_id)
            .group_by(EmailEvent.event_type)
        )

        counts = {row.event_type: row.count for row in result.all()}

        # 2. Get total sent from deliveries
        from core.models.execution import CampaignDelivery
        sent_result = await self.db.execute(
            select(func.count(CampaignDelivery.id))
            .where(
                CampaignDelivery.campaign_id == campaign_id,
                CampaignDelivery.status.in_(["sent", "delivered"])
            )
        )
        total_sent = sent_result.scalar() or 0

        # 3. Calculate metrics
        stats_dict = {
            "campaign_id": campaign_id,
            "total_sent": total_sent,
            "total_delivered": counts.get("delivered", 0),
            "total_bounced": counts.get("bounced", 0),
            "total_deferred": counts.get("deferred", 0),
            "total_opened": counts.get("opened", 0),
            "total_clicked": counts.get("clicked", 0),
            "total_replied": counts.get("replied", 0),
            "total_meetings_booked": counts.get("meeting_booked", 0),
            "total_unsubscribed": counts.get("unsubscribed", 0),
            "total_spam_complaints": counts.get("spam", 0),
        }

        calculated = calculate_rates(stats_dict)

        # 4. Update or create CampaignMetrics
        metric_result = await self.db.execute(
            select(CampaignMetrics).where(CampaignMetrics.campaign_id == campaign_id)
        )
        metrics = metric_result.scalars().first()

        if not metrics:
            metrics = CampaignMetrics(**calculated.model_dump())
            self.db.add(metrics)
        else:
            for key, value in calculated.model_dump().items():
                setattr(metrics, key, value)

        await self.db.commit()
        logger.info(f"Aggregated metrics for campaign {campaign_id}")
