"""
Research Profile Agent

Generates a structured research profile for a company to support personalization.
Caches profile to database and supports force refresh or auto-invalidation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.researcher.enrichment_providers import enrichment_registry
from core.llm import get_llm_provider
from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.models.research_profile import ResearchProfile
from core.utils.exceptions import NotFoundError

log = get_logger(__name__)

PROFILE_SCHEMA = {
    "type": "OBJECT",
    "description": "Structured company research profile for outreach personalization.",
    "properties": {
        "summary": {
            "type": "STRING",
            "description": "A concise executive summary of what the company does and its industry position."
        },
        "hiring_signals": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "insight": {"type": "STRING"},
                    "source_url": {"type": "STRING"}
                },
                "required": ["insight", "source_url"]
            },
            "description": "Signals of active hiring with source URL attributions."
        },
        "growth_indicators": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "insight": {"type": "STRING"},
                    "source_url": {"type": "STRING"}
                },
                "required": ["insight", "source_url"]
            },
            "description": "Signs of company growth with source URL attributions."
        },
        "public_pain_points": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "insight": {"type": "STRING"},
                    "source_url": {"type": "STRING"}
                },
                "required": ["insight", "source_url"]
            },
            "description": "Current scaling or product pain points with source URL attributions."
        },
        "why_now": {
            "type": "STRING",
            "description": "Urgency assessment of why this company needs Outur AI right now."
        },
        "recommended_pitch": {
            "type": "STRING",
            "description": "Main value proposition pitch for the outreach."
        },
        "best_contact": {
            "type": "OBJECT",
            "properties": {
                "full_name": {"type": "STRING"},
                "job_title": {"type": "STRING"},
                "rationale": {"type": "STRING"}
            },
            "required": ["full_name", "job_title", "rationale"],
            "description": "Best contact details and priority rationale."
        },
        "outreach_angles": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Talking points tailored to their context."
        },
        "next_recommended_action": {
            "type": "STRING",
            "description": "Next concrete action to take for outreach."
        },
        "llm_confidence": {
            "type": "INTEGER",
            "description": "Confidence of the LLM generation (0 to 100)."
        },
        "data_quality": {
            "type": "INTEGER",
            "description": "Information completeness and validation status (0 to 100)."
        },
        "freshness_score": {
            "type": "INTEGER",
            "description": "Freshness based on update latency (0 to 100)."
        }
    },
    "required": [
        "summary",
        "hiring_signals",
        "growth_indicators",
        "public_pain_points",
        "why_now",
        "recommended_pitch",
        "outreach_angles",
        "next_recommended_action",
        "llm_confidence",
        "data_quality",
        "freshness_score"
    ]
}


def get_mock_profile(
    company_name: str,
    contacts: list[Contact],
    lead_score: int,
    enrichment_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Generates dynamic, structured mock research profiles.
    """
    co_clean = company_name.strip()
    co_slug = co_clean.lower().replace(" ", "").replace(".", "")

    news_insights = []
    social_insights = []
    careers_insights = []

    for prov_name, prov_val in enrichment_data.items():
        insights_list = prov_val.get("insights", [])
        for item in insights_list:
            mapped_item = {"insight": item["text"], "source_url": item["source_url"]}
            if prov_name == "news":
                news_insights.append(mapped_item)
            elif prov_name == "social":
                social_insights.append(mapped_item)
            elif prov_name == "careers_analyser":
                careers_insights.append(mapped_item)

    if not news_insights:
        news_insights.append({
            "insight": f"{co_clean} announces expansions and AI integrations.",
            "source_url": f"https://{co_slug}.com/news/1"
        })
    if not social_insights:
        social_insights.append({
            "insight": f"LinkedIn followers growth of 18.5% indicating strong brand expansion for {co_clean}.",
            "source_url": f"https://linkedin.com/company/{co_slug}"
        })
    if not careers_insights:
        careers_insights.append({
            "insight": f"Active hiring identified for roles such as Senior Software Engineer (Backend) and Product Manager.",
            "source_url": f"https://{co_slug}.com/careers"
        })
        careers_insights.append({
            "insight": "Hiring pain point: Scale backend API performance.",
            "source_url": f"https://{co_slug}.com/careers/jobs/eng-1"
        })

    best_c = None
    if contacts:
        first_c = contacts[0]
        best_c = {
            "full_name": first_c.full_name,
            "job_title": first_c.job_title,
            "rationale": f"Key HR decision-maker with a contact confidence score of {first_c.confidence_score}."
        }
    else:
        best_c = {
            "full_name": "No contacts discovered",
            "job_title": "HR Manager",
            "rationale": "Fallback priority assigned as no specific decision maker could be found."
        }

    return {
        "summary": f"{co_clean} is an innovative enterprise focusing on modern scalability within its market sector. Recent milestones include product expansions and AI integrations.",
        "hiring_signals": careers_insights[:1],
        "growth_indicators": social_insights + news_insights[1:2],
        "public_pain_points": [careers_insights[-1]] if len(careers_insights) > 1 else careers_insights,
        "why_now": f"The company's rapid hiring indicates team growth, while backend scaling bottlenecks represent immediate friction Outur AI can alleviate.",
        "recommended_pitch": f"Automate lead sourcing and candidate outreach workflows directly for {co_clean}'s talent acquisition team using autonomous agent squads.",
        "best_contact": best_c,
        "outreach_angles": [
            f"Offer to streamline {co_clean}'s outbound campaigns with custom AI agents.",
            f"Suggest automated sourcing for active tech recruitments."
        ],
        "next_recommended_action": f"Draft custom email sequencing for {best_c['full_name']} highlighting candidate generation capabilities.",
        "llm_confidence": 95,
        "data_quality": 85,
        "freshness_score": 90
    }


class ResearchProfileAgent:
    """
    Agent to build research profiles for outreach guidance.
    """

    agent_name: str = "research_profile"

    def __init__(self) -> None:
        log.debug("ResearchProfileAgent initialised")

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Research Profile Agent.

        Parameters
        ----------
        company_id: str | uuid.UUID | None
            The ID of the company to profile.
        company: Company | None
            An already loaded Company object.
        refresh: bool
            Force regeneration/refresh of profile. Defaults to False.
        session: AsyncSession | None
            Optional database session.
        """
        log.info("Running Research Profile Agent", inputs=list(kwargs.keys()))

        company_id = kwargs.get("company_id")
        company = kwargs.get("company")
        refresh = kwargs.get("refresh", False)
        session_param = kwargs.get("session")

        try:
            if isinstance(session_param, AsyncSession):
                result = await self._execute_agent(
                    company_id=company_id,
                    company=company,
                    refresh=refresh,
                    session=session_param,
                    commit=False
                )
            else:
                async with async_session_factory() as local_session:
                    try:
                        result = await self._execute_agent(
                            company_id=company_id,
                            company=company,
                            refresh=refresh,
                            session=local_session,
                            commit=True
                        )
                    except Exception:
                        await local_session.rollback()
                        raise
            return result
        except NotFoundError as e:
            log.error("Company not found during profiling", error=e.detail)
            return {
                "success": False,
                "data": {},
                "errors": [e.detail]
            }
        except Exception as e:
            log.error("Failed to run Research Profile Agent", error=str(e))
            return {
                "success": False,
                "data": {},
                "errors": [str(e)]
            }

    async def _execute_agent(
        self,
        company_id: Any,
        company: Any,
        refresh: bool,
        session: AsyncSession,
        commit: bool = True
    ) -> dict[str, Any]:
        # 1. Resolve Company
        company_obj: Company | None = None
        if company and isinstance(company, Company):
            company_obj = company
        elif company_id:
            if isinstance(company_id, str):
                try:
                    resolved_uuid = uuid.UUID(company_id)
                except ValueError:
                    raise NotFoundError("Company", company_id)
            else:
                resolved_uuid = company_id

            stmt = select(Company).where(Company.id == resolved_uuid)
            res = await session.execute(stmt)
            company_obj = res.scalar_one_or_none()

        if not company_obj:
            raise NotFoundError("Company", company_id)

        # Load contacts and score context
        contacts_stmt = select(Contact).where(Contact.company_id == company_obj.id)
        contacts_res = await session.execute(contacts_stmt)
        contacts = list(contacts_res.scalars().all())

        # 2. Check Database Cache & Cache Invalidation
        profile_stmt = select(ResearchProfile).where(ResearchProfile.company_id == company_obj.id)
        profile_res = await session.execute(profile_stmt)
        existing_profile = profile_res.scalar_one_or_none()

        is_invalidated = False
        if existing_profile:
            # Auto-invalidate if company updated_at is newer than last_verified_at
            if company_obj.updated_at > existing_profile.last_verified_at:
                is_invalidated = True
                log.info("Invalidated cached profile: company has newer updates", company=company_obj.name)

            # Auto-invalidate if any contact updated_at is newer than last_verified_at
            for contact in contacts:
                if contact.updated_at > existing_profile.last_verified_at:
                    is_invalidated = True
                    log.info("Invalidated cached profile: contact has newer updates", contact=contact.full_name)

        if existing_profile and not refresh and not is_invalidated:
            log.info("Returning cached ResearchProfile from DB", company=company_obj.name)
            return {
                "success": True,
                "data": {
                    "company_id": str(company_obj.id),
                    "employees": existing_profile.employees,
                    "revenue_estimated": existing_profile.revenue_estimated,
                    "funding": existing_profile.funding,
                    "technologies_used": existing_profile.technologies_used,
                    "competitors": existing_profile.competitors,
                    "hr_maturity": existing_profile.hr_maturity,
                    "recent_news": existing_profile.recent_news,
                    "hiring_signals": existing_profile.hiring_signals,
                    "growth_indicators": existing_profile.growth_indicators,
                    "public_pain_points": existing_profile.public_pain_points,
                    "ai_adoption_signals": existing_profile.ai_adoption_signals,
                    "opportunity_score": existing_profile.opportunity_score,
                    "why_now_score": existing_profile.why_now_score,
                    "raw_evidence": existing_profile.raw_evidence,
                    "last_verified_at": existing_profile.last_verified_at.isoformat()
                },
                "errors": []
            }

        lead_score = company_obj.score or 0

        # 3. Fetch Enrichment Sources in Parallel from dynamically registered registry
        providers = enrichment_registry.get_providers()
        enrich_tasks = [
            p.enrich(company_obj.name, company_obj.domain)
            for p in providers
        ]
        enrich_results = await asyncio.gather(*enrich_tasks, return_exceptions=True)

        enrichment_data: dict[str, Any] = {}
        raw_evidence: dict[str, Any] = {}
        errors: list[str] = []
        for p, r in zip(providers, enrich_results):
            if isinstance(r, Exception):
                log.error(f"Enrichment provider {p.name} failed", error=str(r))
                errors.append(f"Provider {p.name} failed: {r}")
            else:
                enrichment_data[p.name] = r
                raw_evidence[p.name] = r.get("raw_evidence", {})

        # 4. Synthesize Context with Intelligence Engine
        from agents.research.intelligence_engine import ResearchIntelligenceEngine
        engine = ResearchIntelligenceEngine()
        
        log.debug("Synthesizing structured intelligence", company=company_obj.name)
        profile_data = await engine.analyze_company(
            company_name=company_obj.name,
            domain=company_obj.domain,
            enrichment_data=enrichment_data
        )

        # 5. Save or update DB
        last_ver = datetime.utcnow()

        # Store the engine's why now analysis inside raw_evidence
        raw_evidence["why_now_analysis"] = profile_data.get("why_now_analysis", {})

        if existing_profile:
            existing_profile.employees = profile_data.get("employees")
            existing_profile.revenue_estimated = profile_data.get("revenue_estimated")
            existing_profile.funding = profile_data.get("funding")
            existing_profile.technologies_used = profile_data.get("technologies_used", [])
            existing_profile.competitors = profile_data.get("competitors", [])
            existing_profile.hr_maturity = profile_data.get("hr_maturity")
            existing_profile.recent_news = profile_data.get("recent_news", [])
            existing_profile.hiring_signals = profile_data.get("hiring_signals", [])
            existing_profile.growth_indicators = profile_data.get("growth_indicators", [])
            existing_profile.public_pain_points = profile_data.get("public_pain_points", [])
            existing_profile.ai_adoption_signals = profile_data.get("ai_adoption_signals", [])
            existing_profile.opportunity_score = profile_data.get("opportunity_score", 0)
            existing_profile.why_now_score = profile_data.get("why_now_score", 0)
            existing_profile.raw_evidence = raw_evidence
            existing_profile.last_verified_at = last_ver
            session.add(existing_profile)
        else:
            new_profile = ResearchProfile(
                company_id=company_obj.id,
                employees=profile_data.get("employees"),
                revenue_estimated=profile_data.get("revenue_estimated"),
                funding=profile_data.get("funding"),
                technologies_used=profile_data.get("technologies_used", []),
                competitors=profile_data.get("competitors", []),
                hr_maturity=profile_data.get("hr_maturity"),
                recent_news=profile_data.get("recent_news", []),
                hiring_signals=profile_data.get("hiring_signals", []),
                growth_indicators=profile_data.get("growth_indicators", []),
                public_pain_points=profile_data.get("public_pain_points", []),
                ai_adoption_signals=profile_data.get("ai_adoption_signals", []),
                opportunity_score=profile_data.get("opportunity_score", 0),
                why_now_score=profile_data.get("why_now_score", 0),
                raw_evidence=raw_evidence,
                last_verified_at=last_ver
            )
            session.add(new_profile)

        if commit:
            await session.commit()
        else:
            await session.flush()

        # Combine results to return
        profile_data["company_id"] = str(company_obj.id)
        profile_data["raw_evidence"] = raw_evidence
        profile_data["last_verified_at"] = last_ver.isoformat()

        return {
            "success": True,
            "data": profile_data,
            "errors": errors
        }
