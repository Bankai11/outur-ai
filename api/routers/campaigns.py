"""API router for Campaign resources."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from agents.campaign_manager import generate_outreach_drafts, export_campaign_drafts
from core.models.campaign import Campaign
from core.models.outreach_draft import OutreachDraft
from core.utils.pagination import OffsetParams, PaginatedResponse
from core.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class CampaignCreateSchema(BaseModel):
    name: str
    filters: dict[str, Any] | None = None
    selected_companies: list[UUID]
    selected_contacts: list[UUID]


class CampaignSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    filters: dict[str, Any] | None = None
    selected_companies: list[str]
    selected_contacts: list[str]
    status: str


class OutreachDraftSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    contact_id: UUID
    subject: str
    body: str
    status: str


class GenerateResponse(BaseModel):
    success: bool
    data: list[OutreachDraftSchema]
    errors: list[str]


class ExportResponse(BaseModel):
    success: bool
    data: Any
    errors: list[str]


class EnrichedDraftSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft: OutreachDraftSchema
    contact_name: str
    contact_title: str
    contact_confidence: int
    company_name: str
    opportunity_score: int
    why_now_score: int
    hiring_signals: list[str]
    recent_news: list[str]
    pain_points: list[str]


class CampaignDraftsResponse(BaseModel):
    success: bool
    data: list[EnrichedDraftSchema]
    errors: list[str]


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=CampaignSchema, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreateSchema,
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    """
    Create a new outreach campaign with company and contact targets.
    """
    log.info("Creating campaign", name=payload.name)
    
    # Map UUIDs to string representation for JSON compatibility
    co_str_list = [str(co_id) for co_id in payload.selected_companies]
    con_str_list = [str(con_id) for con_id in payload.selected_contacts]

    campaign = Campaign(
        name=payload.name,
        filters=payload.filters,
        selected_companies=co_str_list,
        selected_contacts=con_str_list,
        status="draft"
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


@router.get("", response_model=PaginatedResponse[CampaignSchema])
async def list_campaigns(
    params: OffsetParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[CampaignSchema]:
    """
    List all campaigns with offset pagination.
    """
    log.info("Listing campaigns", offset=params.offset)

    count_stmt = select(func.count()).select_from(Campaign)
    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = select(Campaign).order_by(Campaign.created_at.desc()).offset(params.offset).limit(params.limit)
    res = await session.execute(stmt)
    items = res.scalars().all()

    return PaginatedResponse.create(items=items, total=total, params=params)


@router.post("/{id}/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_campaign_drafts(
    id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Trigger the Campaign Manager to draft personalized outreach emails for all campaign contacts.
    """
    log.info("Generating drafts for campaign", id=str(id))
    try:
        drafts = await generate_outreach_drafts(campaign_id=id, session=session)
        return {
            "success": True,
            "data": drafts,
            "errors": []
        }
    except Exception as e:
        log.error("Failed to generate campaign drafts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{id}/drafts", response_model=CampaignDraftsResponse, status_code=status.HTTP_200_OK)
async def get_campaign_drafts(
    id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Get all generated drafts for a campaign, enriched with contact and company intelligence.
    """
    from core.models.contact import Contact
    from core.models.company import Company
    from core.models.research_profile import ResearchProfile

    stmt = select(OutreachDraft).where(OutreachDraft.campaign_id == id)
    res = await session.execute(stmt)
    drafts = res.scalars().all()

    enriched_drafts = []
    for d in drafts:
        contact_stmt = select(Contact).where(Contact.id == d.contact_id)
        contact_res = await session.execute(contact_stmt)
        contact = contact_res.scalar_one_or_none()

        if not contact:
            continue

        company_stmt = select(Company).where(Company.id == contact.company_id)
        company_res = await session.execute(company_stmt)
        company = company_res.scalar_one_or_none()
        company_name = company.name if company else "Unknown"

        profile_stmt = select(ResearchProfile).where(ResearchProfile.company_id == contact.company_id)
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()

        enriched_drafts.append({
            "draft": d,
            "contact_name": contact.full_name,
            "contact_title": contact.job_title,
            "contact_confidence": contact.confidence_score,
            "company_name": company_name,
            "opportunity_score": profile.opportunity_score if profile else 0,
            "why_now_score": profile.why_now_score if profile else 0,
            "hiring_signals": [h.get("insight", "") for h in profile.hiring_signals] if profile else [],
            "recent_news": [n.get("title", "") for n in profile.recent_news] if profile else [],
            "pain_points": [p.get("insight", "") for p in profile.public_pain_points] if profile else []
        })

    return {
        "success": True,
        "data": enriched_drafts,
        "errors": []
    }


@router.post("/{id}/export", status_code=status.HTTP_200_OK)
async def export_campaign_outreach(
    id: UUID,
    format: str = Query(..., description="Export format: csv, gmail_draft, or outlook_draft"),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """
    Export generated outreach drafts in CSV, Gmail Draft MIME, or Outlook draft creation payload formats.
    """
    log.info("Exporting campaign outreach", id=str(id), format=format)
    try:
        export_data = await export_campaign_drafts(campaign_id=id, export_format=format, session=session)
        
        # If CSV, return a direct file download stream
        if format.strip().lower() == "csv":
            return Response(
                content=export_data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=campaign_{id}_export.csv"
                }
            )
            
        # For API format JSON payloads
        return {
            "success": True,
            "data": export_data,
            "errors": []
        }
    except Exception as e:
        log.error("Failed to export campaign drafts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{id}/send", status_code=status.HTTP_200_OK)
async def send_campaign_outreach(
    id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Send all generated outreach drafts for the given campaign via the configured email provider.
    """
    from datetime import datetime
    from core.services.email import get_email_provider
    from core.models.contact import Contact
    
    log.info("Sending campaign outreach", campaign_id=str(id))
    try:
        # Fetch unsent drafts with their contact emails
        stmt = (
            select(OutreachDraft, Contact.email)
            .join(Contact, OutreachDraft.contact_id == Contact.id)
            .where(
                OutreachDraft.campaign_id == id,
                OutreachDraft.status == "draft",
                OutreachDraft.sent_at.is_(None)
            )
        )
        res = await session.execute(stmt)
        drafts_with_email = res.all()
        
        if not drafts_with_email:
            return {"success": True, "message": "No unsent drafts found for this campaign.", "sent_count": 0}

        email_provider = get_email_provider()
        sent_count = 0
        
        for draft, contact_email in drafts_with_email:
            if not contact_email:
                log.warning("Skipping draft due to missing contact email", draft_id=str(draft.id))
                draft.status = "failed"
                continue
                
            result = await email_provider.send_email(
                to_email=contact_email,
                subject=draft.subject,
                body=draft.body
            )
            
            if result.get("success"):
                draft.status = "sent"
                draft.sent_at = datetime.utcnow()
                if result.get("message_id"):
                    draft.external_id = result["message_id"]
                sent_count += 1
            else:
                log.error("Failed to send draft", draft_id=str(draft.id), error=result.get("error"))
                draft.status = "failed"
                
        await session.commit()
        
        return {
            "success": True,
            "message": f"Successfully sent {sent_count} emails.",
            "sent_count": sent_count
        }
        
    except Exception as e:
        log.error("Failed to send campaign outreach", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

