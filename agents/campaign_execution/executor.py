"""Campaign Executor Service."""

import logging
from uuid import UUID
from typing import List
from sqlalchemy import select
from arq import create_pool

from core.database.engine import async_session_factory
from core.models.campaign import Campaign
from core.models.contact import Contact
from core.models.outreach_draft import OutreachDraft
from core.models.execution import CampaignRun, CampaignDelivery
from core.queue.client import get_redis_pool

from agents.campaign_execution.models import DraftPayload, ProviderConfig

log = logging.getLogger(__name__)


class CampaignExecutor:
    """
    Orchestrates the asynchronous delivery of a completed campaign.
    Fetches generated drafts and enqueues them for delivery via ARQ.
    """
    
    def __init__(self, provider_config: ProviderConfig):
        self.provider_config = provider_config

    async def execute_campaign(self, campaign_id: UUID) -> UUID:
        """
        Start the execution run for a campaign.
        
        Args:
            campaign_id: The ID of the campaign to execute.
            
        Returns:
            The ID of the newly created CampaignRun.
        """
        redis_pool = await get_redis_pool()
        
        async with async_session_factory() as session:
            # 1. Verify Campaign exists and has drafts
            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found.")
                
            # Fetch all drafts ready to be sent (must be approved!)
            stmt = (
                select(OutreachDraft, Contact)
                .join(Contact, OutreachDraft.contact_id == Contact.id)
                .where(OutreachDraft.campaign_id == campaign_id)
                .where(OutreachDraft.status == "draft")
                .where(OutreachDraft.approval_status == "approved")
            )
            result = await session.execute(stmt)
            drafts_and_contacts = result.all()
            
            if not drafts_and_contacts:
                log.warning(f"No pending approved drafts found for campaign {campaign_id}.")
                # Still create a run, just immediately empty
                run = CampaignRun(
                    campaign_id=campaign_id,
                    status="completed",
                    total_drafts=0
                )
                session.add(run)
                await session.commit()
                return run.id
                
            # Initialize Safety Guard
            from agents.campaign_execution.safety_guard import CampaignSafetyGuard
            safety_guard = CampaignSafetyGuard(session=session)
            
            current_run_count = 0
            domain_counts = {}
            safe_drafts = []
            
            # Evaluate safety for each draft
            for draft, contact in drafts_and_contacts:
                is_safe, reason = await safety_guard.evaluate_draft(draft, contact, current_run_count, domain_counts)
                if not is_safe:
                    log.warning(f"Draft {draft.id} for {contact.email} blocked: {reason}")
                    draft.status = "failed"
                    draft.approval_status = f"blocked_by_safety: {reason}"
                    session.add(draft)
                    continue
                
                safe_drafts.append((draft, contact))
                current_run_count += 1
                domain = contact.email.split("@")[-1].lower() if contact.email else ""
                if domain:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    
            if not safe_drafts:
                log.warning(f"All drafts blocked by safety guard for campaign {campaign_id}.")
                run = CampaignRun(campaign_id=campaign_id, status="completed", total_drafts=0)
                session.add(run)
                await session.commit()
                return run.id

            # 2. Create CampaignRun
            run = CampaignRun(
                campaign_id=campaign_id,
                status="running",
                total_drafts=len(safe_drafts)
            )
            session.add(run)
            await session.flush() # Get run.id
            
            # 3. Queue Jobs
            for draft, contact in safe_drafts:
                # Create CampaignDelivery record
                delivery = CampaignDelivery(
                    run_id=run.id,
                    draft_id=draft.id,
                    status="queued",
                    provider_name=self.provider_config.provider_name
                )
                session.add(delivery)
                await session.flush() # Get delivery.id
                
                # Build Payload
                payload = DraftPayload(
                    draft_id=draft.id,
                    campaign_id=campaign.id,
                    contact_id=contact.id,
                    contact_email=contact.email,
                    subject=draft.subject,
                    body=draft.body
                )
                
                # Enqueue Job
                await redis_pool.enqueue_job(
                    "send_email_job",
                    str(delivery.id),
                    payload.model_dump(mode="json"),
                    self.provider_config.model_dump(mode="json"),
                    0 # attempt
                )
                
                # Mark draft as queued
                draft.status = "queued"
                
            await session.commit()
            log.info(f"Enqueued {len(safe_drafts)} emails for campaign {campaign_id} in run {run.id}")
            return run.id
