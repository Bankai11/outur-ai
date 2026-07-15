"""Event Processor for the analytics subsystem.

Reads raw ProviderEvents, standardizes them, creates EmailEvents, and updates RecipientActivities.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import exc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents.analytics.models import StandardEventPayload
from core.models.analytics import EmailEvent, EventAudit, ProviderEvent, RecipientActivity
from core.models.execution import CampaignDelivery

logger = logging.getLogger(__name__)

def generate_event_hash(payload: dict[str, Any]) -> str:
    """Generate a deterministic hash for idempotency checking."""
    # Ensure stable sorting for dictionary serialization
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


class EventProcessor:
    """Processes raw webhook events into canonical analytics data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_idempotency(self, event_hash: str) -> bool:
        """Return True if event has already been processed."""
        result = await self.db.execute(
            select(EventAudit).where(EventAudit.event_hash == event_hash)
        )
        return result.scalars().first() is not None

    async def _record_audit(self, event_hash: str, provider_event_id: UUID) -> None:
        """Record the event to prevent duplicate processing."""
        audit = EventAudit(
            event_hash=event_hash,
            processed_at=datetime.now(UTC),
            provider_event_id=provider_event_id
        )
        self.db.add(audit)

    async def process_raw_event(self, provider_event_id: UUID, standard_event: StandardEventPayload) -> None:
        """Process a standardized event into analytics data models."""

        event_hash = generate_event_hash(standard_event.raw_payload)

        if await self._check_idempotency(event_hash):
            logger.info(f"Event {event_hash} already processed. Skipping.")
            return

        # Find the delivery record to get campaign and contact info
        result = await self.db.execute(
            select(CampaignDelivery).where(
                CampaignDelivery.provider_message_id == standard_event.provider_message_id
            )
        )
        delivery = result.scalars().first()

        if not delivery:
            logger.warning(f"Delivery not found for message_id: {standard_event.provider_message_id}")
            return

        # 1. Create EmailEvent
        email_event = EmailEvent(
            delivery_id=delivery.id,
            campaign_id=delivery.campaign_id,
            contact_id=delivery.contact_id,
            event_type=standard_event.event_type,
            occurred_at=standard_event.occurred_at,
            provider_name=standard_event.provider_name,
            provider_message_id=standard_event.provider_message_id,
            event_metadata=standard_event.event_metadata
        )
        self.db.add(email_event)

        # 2. Update RecipientActivity
        await self._update_recipient_activity(
            contact_id=delivery.contact_id,
            campaign_id=delivery.campaign_id,
            event_type=standard_event.event_type,
            occurred_at=standard_event.occurred_at
        )

        # 3. Mark raw event as processed
        if provider_event_id:
            await self.db.execute(
                update(ProviderEvent)
                .where(ProviderEvent.id == provider_event_id)
                .values(processed=True)
            )

        # 4. Record audit hash
        await self._record_audit(event_hash, provider_event_id)

        try:
            await self.db.commit()
            logger.info(f"Processed event {standard_event.event_type} for message {standard_event.provider_message_id}")
        except exc.IntegrityError:
            await self.db.rollback()
            logger.error(f"Integrity error processing event for message {standard_event.provider_message_id}")

    async def _update_recipient_activity(self, contact_id: UUID, campaign_id: UUID, event_type: str, occurred_at: datetime) -> None:
        """Update or create a RecipientActivity record."""
        result = await self.db.execute(
            select(RecipientActivity).where(
                RecipientActivity.contact_id == contact_id,
                RecipientActivity.campaign_id == campaign_id
            )
        )
        activity = result.scalars().first()

        if not activity:
            activity = RecipientActivity(
                contact_id=contact_id,
                campaign_id=campaign_id,
                open_count=0,
                click_count=0
            )
            self.db.add(activity)

        if event_type == "opened":
            activity.open_count += 1
            if not activity.first_opened_at or occurred_at < activity.first_opened_at:
                activity.first_opened_at = occurred_at
            if not activity.last_opened_at or occurred_at > activity.last_opened_at:
                activity.last_opened_at = occurred_at

        elif event_type == "clicked":
            activity.click_count += 1
            if not activity.first_clicked_at or occurred_at < activity.first_clicked_at:
                activity.first_clicked_at = occurred_at
            if not activity.last_clicked_at or occurred_at > activity.last_clicked_at:
                activity.last_clicked_at = occurred_at

        elif event_type == "replied":
            if not activity.replied_at or occurred_at < activity.replied_at:
                activity.replied_at = occurred_at

        elif event_type == "bounced":
            if not activity.bounced_at or occurred_at < activity.bounced_at:
                activity.bounced_at = occurred_at
