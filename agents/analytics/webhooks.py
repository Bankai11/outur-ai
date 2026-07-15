"""Webhook parsers and queue integration for the analytics subsystem.

Converts provider-specific webhooks into standard payloads and queues them.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from agents.analytics.models import StandardEventPayload
from core.queue.client import get_redis_pool

logger = logging.getLogger(__name__)

async def enqueue_event_for_processing(payload: StandardEventPayload, provider_event_id: str) -> None:
    """Send a standardized event to the ARQ background worker."""
    redis = await get_redis_pool()

    # We pass the raw dict to ARQ because passing Pydantic models directly requires custom serialization
    await redis.enqueue_job(
        "process_analytics_event",
        provider_event_id=str(provider_event_id),
        event_dict=payload.model_dump()
    )
    logger.info(f"Enqueued event {payload.event_type} for message {payload.provider_message_id}")

class ResendParser:
    """Parses Resend webhook payloads."""

    EVENT_MAP = {
        "email.sent": "sent",
        "email.delivered": "delivered",
        "email.opened": "opened",
        "email.bounced": "bounced",
        "email.clicked": "clicked",
        "email.complained": "spam",
    }

    @classmethod
    def parse(cls, raw_payload: dict[str, Any]) -> StandardEventPayload | None:
        event_type_raw = raw_payload.get("type")
        data = raw_payload.get("data", {})
        email_id = data.get("email_id")

        if not event_type_raw or not email_id:
            return None

        std_type = cls.EVENT_MAP.get(event_type_raw)
        if not std_type:
            return None

        return StandardEventPayload(
            provider_name="resend",
            provider_message_id=email_id,
            event_type=std_type,
            occurred_at=datetime.now(UTC), # Resend payload often has created_at
            raw_payload=raw_payload,
            event_metadata={}
        )
