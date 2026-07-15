"""Scheduler integration for Decision Engine background jobs."""

from __future__ import annotations

import logging
from uuid import UUID

from core.queue.client import get_redis_pool

logger = logging.getLogger(__name__)


class DecisionScheduler:
    """Enqueues deferred evaluation and action execution jobs onto the ARQ Redis queue."""

    async def schedule_evaluation(
        self, campaign_id: UUID, contact_id: UUID, delay_seconds: int = 0
    ) -> None:
        """Enqueue a background job to evaluate the decision logic for a recipient."""
        redis = await get_redis_pool()
        if delay_seconds > 0:
            await redis.enqueue_job(
                "evaluate_recipient_job", str(campaign_id), str(contact_id), _defer_by=delay_seconds
            )
            logger.info(f"Scheduled evaluation for contact {contact_id} in {delay_seconds} seconds")
        else:
            await redis.enqueue_job("evaluate_recipient_job", str(campaign_id), str(contact_id))
            logger.info(f"Enqueued immediate evaluation for contact {contact_id}")

    async def schedule_followup_generation(
        self, campaign_id: UUID, contact_id: UUID, action_type: str
    ) -> None:
        """Enqueue a background job to generate and execute a follow-up action."""
        redis = await get_redis_pool()
        await redis.enqueue_job(
            "generate_followup_job", str(campaign_id), str(contact_id), action_type
        )
        logger.info(f"Enqueued follow-up generation ({action_type}) for contact {contact_id}")
