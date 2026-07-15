"""ARQ background jobs for the Decision Engine."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from agents.campaign_execution.models import DraftPayload
from agents.campaign_manager import generate_followup_draft
from agents.decision_engine.agent import DecisionEngineAgent
from core.database.engine import async_session_factory
from core.models.contact import Contact
from core.models.execution import CampaignDelivery, CampaignRun

logger = logging.getLogger(__name__)


async def evaluate_recipient_job(ctx: dict, campaign_id_str: str, contact_id_str: str) -> None:
    """ARQ job to run decision engine evaluation for a single contact."""
    campaign_id = UUID(campaign_id_str)
    contact_id = UUID(contact_id_str)

    logger.info(f"Running Decision Engine evaluation job for contact {contact_id}")

    async with async_session_factory() as session:
        agent = DecisionEngineAgent(session)
        await agent.evaluate_contact(campaign_id, contact_id)


async def generate_followup_job(
    ctx: dict, campaign_id_str: str, contact_id_str: str, action_type: str
) -> None:
    """ARQ job to generate a follow-up draft and enqueue it for delivery."""
    campaign_id = UUID(campaign_id_str)
    contact_id = UUID(contact_id_str)

    logger.info(f"Generating follow-up draft for contact {contact_id} (action: {action_type})")

    async with async_session_factory() as session:
        # 1. Generate the draft using CampaignManager's shared logic
        draft = await generate_followup_draft(campaign_id, contact_id, action_type, session)

        # 2. Load Contact
        contact = await session.get(Contact, contact_id)
        if not contact or not contact.email:
            logger.error(f"Contact {contact_id} not found or missing email. Aborting follow-up.")
            return

        # 3. Fetch/Create CampaignRun
        from sqlalchemy import select

        run_stmt = (
            select(CampaignRun)
            .where(CampaignRun.campaign_id == campaign_id, CampaignRun.status == "running")
            .order_by(CampaignRun.created_at.desc())
        )
        run = (await session.execute(run_stmt)).scalars().first()

        if not run:
            run = CampaignRun(campaign_id=campaign_id, status="running", total_drafts=1)
            session.add(run)
            await session.flush()

        # 4. Create CampaignDelivery record
        delivery = CampaignDelivery(
            run_id=run.id, draft_id=draft.id, status="queued", provider_name="mock_provider"
        )
        session.add(delivery)
        await session.flush()

        # 5. Build DraftPayload
        payload = DraftPayload(
            draft_id=draft.id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            contact_email=contact.email,
            subject=draft.subject,
            body=draft.body,
        )

        # 6. Dispatch to CampaignExecutor's email sending job via Redis queue
        redis = ctx["redis"]
        await redis.enqueue_job(
            "send_email_job",
            str(delivery.id),
            payload.model_dump(mode="json"),
            {"provider_name": "mock_provider", "rate_limit_per_minute": 100},
            0,  # attempt count
        )

        # Mark draft as queued
        draft.status = "queued"
        await session.commit()
        logger.info(
            f"Enqueued follow-up email delivery for contact {contact_id} "
            f"with delivery ID {delivery.id}"
        )


async def on_analytics_event(event_type: str, data: dict[str, Any]) -> None:
    """Callback triggered via EventBus to schedule recipient evaluation."""
    from agents.decision_engine.scheduler import DecisionScheduler

    campaign_id = UUID(data["campaign_id"])
    contact_id = UUID(data["contact_id"])

    scheduler = DecisionScheduler()
    await scheduler.schedule_evaluation(campaign_id, contact_id, delay_seconds=0)
