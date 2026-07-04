"""API router for Company resources."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from agents.scout.agent import ScoutAgent
from agents.researcher.agent import ResearcherAgent
from agents.researcher.research_profile_agent import ResearchProfileAgent
from agents.scorer.agent import ScorerAgent
from core.models.company import Company
from core.utils.pagination import OffsetParams, PaginatedResponse
from core.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class ContactSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    job_title: str
    linkedin_url: str | None = None
    email: str | None = None
    source_url: str | None = None
    confidence_score: int


class InsightSchema(BaseModel):
    insight: str
    source_url: str | None = None


class BestContactSchema(BaseModel):
    full_name: str
    job_title: str
    rationale: str


class ResearchProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    summary: str
    hiring_signals: list[InsightSchema]
    growth_indicators: list[InsightSchema]
    public_pain_points: list[InsightSchema]
    why_now: str
    recommended_pitch: str
    best_contact: BestContactSchema | None = None
    outreach_angles: list[str]
    next_recommended_action: str
    raw_evidence: dict[str, Any] = {}
    llm_confidence: int
    data_quality: int
    freshness_score: int
    last_verified_at: Any


class CompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    website: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    location: str | None = None
    careers_page: str | None = None
    source: str
    score: int | None = None
    tier: str | None = None
    score_signals: list[str] | None = None
    contacts: list[ContactSchema] = []
    research_profile: ResearchProfileSchema | None = None


class DiscoveryRequest(BaseModel):
    industry: str | None = None
    location: str | None = None
    company_size: str | None = None
    limit: int = Field(default=50, ge=1, le=100)


class DiscoveryResponseData(BaseModel):
    companies: list[CompanySchema]
    total_found: int
    new_count: int
    updated_count: int = 0


class DiscoveryResponse(BaseModel):
    success: bool
    data: DiscoveryResponseData
    errors: list[str]


class ResearchResponseData(BaseModel):
    contacts: list[ContactSchema]


class ResearchResponse(BaseModel):
    success: bool
    data: ResearchResponseData
    errors: list[str]


class ScoreResponseData(BaseModel):
    company_id: str
    score: int
    tier: str
    signals: list[str]


class ScoreResponse(BaseModel):
    success: bool
    data: ScoreResponseData
    errors: list[str]


class ProfileResponse(BaseModel):
    success: bool
    data: ResearchProfileSchema
    errors: list[str]


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[CompanySchema])
async def list_companies(
    params: OffsetParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[CompanySchema]:
    """
    List discovered companies with offset-based pagination.
    """
    log.info("Listing companies", page=params.page, page_size=params.page_size)

    # 1. Total count query
    count_stmt = select(func.count()).select_from(Company)
    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    # 2. Results query with eager loaded contacts to prevent lazy-load errors
    stmt = (
        select(Company)
        .order_by(Company.created_at.desc())
        .offset(params.offset)
        .limit(params.limit)
    )
    results_res = await session.execute(stmt)
    items = results_res.scalars().all()

    # Load contacts and research_profile relationships explicitly
    from sqlalchemy.orm import selectinload
    load_stmt = (
        select(Company)
        .options(
            selectinload(Company.contacts),
            selectinload(Company.research_profile)
        )
        .where(Company.id.in_([c.id for c in items]))
        .order_by(Company.created_at.desc())
    )
    if items:
        loaded_res = await session.execute(load_stmt)
        items = list(loaded_res.scalars().all())

    return PaginatedResponse.create(
        items=items,
        total=total,
        params=params,
    )


@router.post("/discover", response_model=DiscoveryResponse, status_code=status.HTTP_201_CREATED)
async def discover_companies(
    request: DiscoveryRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Trigger the Scout Discovery Agent to search for companies matching criteria.
    Results are saved, validated, and deduplicated in the database.
    """
    log.info(
        "Triggering company discovery",
        industry=request.industry,
        location=request.location,
        company_size=request.company_size,
    )

    agent = ScoutAgent()
    result = await agent.run(
        industry=request.industry,
        location=request.location,
        company_size=request.company_size,
        limit=request.limit,
        session=session,
    )

    if not result.get("success") and not result.get("data", {}).get("companies"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discovery failed: {', '.join(result.get('errors', []))}",
        )

    return result


@router.post("/discover/csv", response_model=DiscoveryResponse, status_code=status.HTTP_201_CREATED)
async def discover_companies_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Upload a CSV file containing company records.
    The agent parses, normalises, validates, deduplicates and saves them.
    """
    log.info("Triggering CSV import discovery", filename=file.filename)

    try:
        content = await file.read()
        csv_text = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded CSV file: {e}",
        )

    agent = ScoutAgent()
    result = await agent.run(
        csv_content=csv_text,
        session=session,
    )

    if not result.get("success") and not result.get("data", {}).get("companies"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV Import failed: {', '.join(result.get('errors', []))}",
        )

    return result


@router.post("/{company_id}/research", response_model=ResearchResponse, status_code=status.HTTP_201_CREATED)
async def research_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Trigger the Researcher Agent to discover HR/hiring decision-makers for a company.
    """
    log.info("Triggering company research", company_id=str(company_id))

    agent = ResearcherAgent()
    result = await agent.run(company_id=company_id, session=session)

    if not result.get("success") and not result.get("data", {}).get("contacts"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Research failed: {', '.join(result.get('errors', []))}",
        )

    return result


@router.post("/{company_id}/score", response_model=ScoreResponse, status_code=status.HTTP_200_OK)
async def score_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Trigger the Scorer Agent to evaluate fit, growth, and contact completeness of a company.
    """
    log.info("Triggering company scoring", company_id=str(company_id))

    agent = ScorerAgent()
    result = await agent.run(company_id=company_id, session=session)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scoring failed: {', '.join(result.get('errors', []))}",
        )

    return result


@router.post("/{company_id}/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def profile_company(
    company_id: UUID,
    refresh: bool = False,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Generate or fetch the cached research context profile for a company.
    """
    log.info("Triggering company profiling", company_id=str(company_id), refresh=refresh)

    agent = ResearchProfileAgent()
    result = await agent.run(company_id=company_id, refresh=refresh, session=session)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profiling failed: {', '.join(result.get('errors', []))}",
        )

    return result
