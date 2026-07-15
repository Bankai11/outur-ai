"""Data access layer for the Decision Engine context gathering."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.decision_engine.models import EvaluationContext
from core.models.analytics import CampaignMetrics, EmailEvent, RecipientActivity
from core.models.company import Company
from core.models.contact import Contact
from core.models.decision import RecipientLifecycle
from core.models.execution import CampaignDelivery
from core.models.research_profile import ResearchProfile

logger = logging.getLogger(__name__)


class DecisionRepository:
    """Aggregates all campaign, contact, company, and activity metrics to form
    an EvaluationContext.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_evaluation_context(
        self, campaign_id: UUID, contact_id: UUID
    ) -> EvaluationContext:
        """Query all tables to construct the complete EvaluationContext for the recipient."""
        # 1. Fetch lifecycle
        lifecycle_stmt = select(RecipientLifecycle).where(
            RecipientLifecycle.campaign_id == campaign_id,
            RecipientLifecycle.contact_id == contact_id,
        )
        lifecycle = (await self.db.execute(lifecycle_stmt)).scalars().first()
        current_state = lifecycle.state if lifecycle else "CREATED"

        # 2. Fetch Contact and Company
        contact_stmt = select(Contact).where(Contact.id == contact_id)
        contact = (await self.db.execute(contact_stmt)).scalars().first()

        company = None
        company_id = None
        company_context = {}
        if contact:
            company_id = contact.company_id
            company_stmt = select(Company).where(Company.id == company_id)
            company = (await self.db.execute(company_stmt)).scalars().first()
            if company:
                company_context = {
                    "name": company.name,
                    "domain": company.domain,
                    "industry": company.industry,
                    "size": company.size,
                    "location": company.location,
                }

        # 3. Fetch Research Profile
        opportunity_score = 50.0
        buying_signals = {}
        if company_id:
            profile_stmt = select(ResearchProfile).where(ResearchProfile.company_id == company_id)
            profile = (await self.db.execute(profile_stmt)).scalars().first()
            if profile:
                opportunity_score = float(profile.opportunity_score)
                buying_signals = {
                    "hiring": profile.hiring_signals,
                    "pain_points": profile.public_pain_points,
                    "tech": profile.technologies_used,
                    "growth": profile.growth_indicators,
                }

        # 4. Fetch Recipient Activity
        activity_stmt = select(RecipientActivity).where(
            RecipientActivity.campaign_id == campaign_id, RecipientActivity.contact_id == contact_id
        )
        activity = (await self.db.execute(activity_stmt)).scalars().first()
        activity_dict = {}
        if activity:
            activity_dict = {
                "open_count": activity.open_count,
                "click_count": activity.click_count,
                "first_opened_at": activity.first_opened_at.isoformat()
                if activity.first_opened_at
                else None,
                "first_clicked_at": activity.first_clicked_at.isoformat()
                if activity.first_clicked_at
                else None,
                "replied_at": activity.replied_at.isoformat() if activity.replied_at else None,
                "bounced_at": activity.bounced_at.isoformat() if activity.bounced_at else None,
            }

        # 5. Fetch Campaign Metrics
        metrics_stmt = select(CampaignMetrics).where(CampaignMetrics.campaign_id == campaign_id)
        metrics = (await self.db.execute(metrics_stmt)).scalars().first()
        metrics_dict = {}
        if metrics:
            metrics_dict = {
                "total_sent": metrics.total_sent,
                "total_delivered": metrics.total_delivered,
                "total_opened": metrics.total_opened,
                "total_clicked": metrics.total_clicked,
                "health_score": metrics.health_score,
            }

        # 6. Fetch Email Events
        events_stmt = (
            select(EmailEvent)
            .where(EmailEvent.campaign_id == campaign_id, EmailEvent.contact_id == contact_id)
            .order_by(EmailEvent.occurred_at.desc())
        )
        events = (await self.db.execute(events_stmt)).scalars().all()
        events_list = [
            {
                "event_type": ev.event_type,
                "occurred_at": ev.occurred_at.isoformat(),
                "provider_name": ev.provider_name,
                "metadata": ev.event_metadata,
            }
            for ev in events
        ]

        # 7. Count previous deliveries
        from core.models.outreach_draft import OutreachDraft

        prev_emails_stmt = (
            select(func.count(CampaignDelivery.id))
            .join(OutreachDraft, CampaignDelivery.draft_id == OutreachDraft.id)
            .where(
                OutreachDraft.campaign_id == campaign_id,
                OutreachDraft.contact_id == contact_id,
                CampaignDelivery.status == "sent",
            )
        )
        prev_emails_count = (await self.db.execute(prev_emails_stmt)).scalar() or 0

        # 8. Calculate days since last interaction
        days_since_last_interaction = 0.0
        if events_list:
            last_event_time = datetime.fromisoformat(events_list[0]["occurred_at"])
            delta = datetime.now(UTC) - last_event_time
            days_since_last_interaction = max(0.0, delta.total_seconds() / 86400.0)
        elif lifecycle and lifecycle.state_entered_at:
            delta = datetime.now(UTC) - lifecycle.state_entered_at.replace(tzinfo=UTC)
            days_since_last_interaction = max(0.0, delta.total_seconds() / 86400.0)

        return EvaluationContext(
            campaign_id=campaign_id,
            contact_id=contact_id,
            current_state=current_state,
            opportunity_score=opportunity_score,
            campaign_metrics=metrics_dict,
            recipient_activity=activity_dict,
            email_events=events_list,
            previous_emails_count=prev_emails_count,
            days_since_last_interaction=days_since_last_interaction,
            buying_signals=buying_signals,
            company_context=company_context,
        )
