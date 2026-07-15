"""API router for analytics endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from agents.analytics.models import CampaignStats
from agents.analytics.service import AnalyticsService
from agents.analytics.webhooks import ResendParser, enqueue_event_for_processing
from api.deps import get_session

log = logging.getLogger(__name__)
router = APIRouter()

@router.post("/webhooks/resend", status_code=status.HTTP_200_OK)
async def analytics_resend_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Receive and enqueue Resend webhooks for the analytics engine."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 1. Record raw webhook
    svc = AnalyticsService(session)
    provider_event_id = await svc.record_raw_webhook("resend", payload)

    # 2. Parse into standard format
    standard_event = ResendParser.parse(payload)
    if not standard_event:
        return {"status": "ignored"}

    # 3. Enqueue for async processing
    await enqueue_event_for_processing(standard_event, str(provider_event_id))

    return {"status": "enqueued"}


@router.get("/campaigns/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_analytics(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Retrieve up-to-date metrics for a campaign."""
    svc = AnalyticsService(session)
    stats = await svc.get_campaign_stats(campaign_id)
    return stats
