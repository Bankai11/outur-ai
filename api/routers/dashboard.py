"""API router for Dashboard metrics."""

from __future__ import annotations

from typing import Any
from datetime import datetime, date
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from core.models.company import Company
from core.models.contact import Contact
from core.models.research_profile import ResearchProfile
from core.models.outreach_draft import OutreachDraft
from core.logger import get_logger

log = get_logger(__name__)
router = APIRouter()

@router.get("/metrics")
async def get_dashboard_metrics(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get high-level metrics for the Lead Intelligence Dashboard."""
    
    # 1. Prospects Today
    today = date.today()
    stmt_prospects_today = select(func.count()).select_from(Company).where(
        func.date(Company.created_at) == today
    )
    res_prospects = await session.execute(stmt_prospects_today)
    prospects_today = res_prospects.scalar() or 0

    # 2. Qualified (Companies that have been researched and scored positively, or just total companies)
    # Let's define qualified as companies with score >= 70 from scout phase
    stmt_qualified = select(func.count()).select_from(Company).where(Company.score >= 70)
    res_qualified = await session.execute(stmt_qualified)
    qualified = res_qualified.scalar() or 0

    # 3. Verified Emails (Contacts with confidence_score >= 90)
    stmt_emails = select(func.count()).select_from(Contact).where(Contact.confidence_score >= 90)
    res_emails = await session.execute(stmt_emails)
    verified_emails = res_emails.scalar() or 0

    # 4. High Opportunity (Research profiles with opportunity_score > 70)
    stmt_high_opp = select(func.count()).select_from(ResearchProfile).where(ResearchProfile.opportunity_score > 70)
    res_high_opp = await session.execute(stmt_high_opp)
    high_opportunity = res_high_opp.scalar() or 0

    # 5. Emails Sent
    stmt_sent = select(func.count()).select_from(OutreachDraft).where(OutreachDraft.status == 'sent')
    res_sent = await session.execute(stmt_sent)
    emails_sent = res_sent.scalar() or 0

    # 6. Replies
    stmt_replies = select(func.count()).select_from(OutreachDraft).where(OutreachDraft.reply_status.is_not(None))
    res_replies = await session.execute(stmt_replies)
    replies = res_replies.scalar() or 0

    # 7. Positive Replies
    stmt_positive = select(func.count()).select_from(OutreachDraft).where(OutreachDraft.reply_status == 'Interested')
    res_positive = await session.execute(stmt_positive)
    positive_replies = res_positive.scalar() or 0

    return {
        "prospects_today": prospects_today,
        "qualified": qualified,
        "verified_emails": verified_emails,
        "high_opportunity": high_opportunity,
        "emails_sent": emails_sent,
        "replies": replies,
        "positive_replies": positive_replies
    }
