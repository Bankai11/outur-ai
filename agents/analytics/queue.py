"""ARQ background jobs for analytics."""

import logging
from typing import Any
from uuid import UUID

from agents.analytics.aggregator import MetricsAggregator
from agents.analytics.models import StandardEventPayload
from agents.analytics.processor import EventProcessor

logger = logging.getLogger(__name__)

async def process_analytics_event(ctx: dict, provider_event_id: str, event_dict: dict[str, Any]) -> None:
    """ARQ job to process a single analytics event."""
    session_factory = ctx["db_session_factory"]

    # Rehydrate Pydantic model
    payload = StandardEventPayload(**event_dict)

    async with session_factory() as session:
        # 1. Process Event
        processor = EventProcessor(session)
        await processor.process_raw_event(UUID(provider_event_id), payload)

        # 2. Extract campaign_id and contact_id to trigger aggregation and publish events
        from sqlalchemy import select
        from core.models.execution import CampaignDelivery
        from core.models.outreach_draft import OutreachDraft

        result = await session.execute(
            select(CampaignDelivery.campaign_id, OutreachDraft.contact_id)
            .join(OutreachDraft, CampaignDelivery.draft_id == OutreachDraft.id)
            .where(CampaignDelivery.provider_message_id == payload.provider_message_id)
        )
        row = result.first()

        if row:
            campaign_id, contact_id = row
            # 3. Aggregate metrics
            aggregator = MetricsAggregator(session)
            await aggregator.aggregate_campaign(campaign_id)
            logger.info(f"Successfully processed analytics for campaign {campaign_id}")
            
            # 4. Publish to EventBus
            from core.event_bus import event_bus
            await event_bus.publish(
                f"email_{payload.event_type}",
                {
                    "campaign_id": str(campaign_id),
                    "contact_id": str(contact_id),
                    "event_type": payload.event_type
                }
            )
        else:
            logger.warning(f"Could not aggregate metrics: no delivery found for message {payload.provider_message_id}")

