"""
Sales Intelligence Agent

Builds the SalesIntelligenceProfile by orchestrating the modular 
SalesIntelligenceEngine and persisting the results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.models.sales_intelligence import SalesIntelligenceProfile
from core.utils.exceptions import NotFoundError
from core.services.company_resolver import resolve_company
from agents.research.sales_intelligence_engine import SalesIntelligenceEngine
from core.database import async_session_factory

log = get_logger(__name__)


class SalesIntelligenceAgent:
    """
    Agent to build sales intelligence profiles for Kultrp outreach guidance.
    """

    agent_name: str = "sales_intelligence"

    def __init__(self) -> None:
        log.debug("SalesIntelligenceAgent initialised")

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Sales Intelligence Agent.

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
        log.info("Running Sales Intelligence Agent", inputs=list(kwargs.keys()))

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
            log.error("Failed to run Sales Intelligence Agent", error=str(e))
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
        company_obj = await resolve_company(company_id, session, company=company)

        # Load contacts
        contacts_stmt = select(Contact).where(Contact.company_id == company_obj.id)
        contacts_res = await session.execute(contacts_stmt)
        contacts = list(contacts_res.scalars().all())

        # 2. Check Database Cache
        profile_stmt = select(SalesIntelligenceProfile).where(SalesIntelligenceProfile.company_id == company_obj.id)
        profile_res = await session.execute(profile_stmt)
        existing_profile = profile_res.scalar_one_or_none()

        is_invalidated = False
        if existing_profile:
            # Auto-invalidate logic based on company or contacts update times
            if company_obj.updated_at > existing_profile.last_verified_at:
                is_invalidated = True
                log.info("Invalidated cached profile: company has newer updates", company=company_obj.name)

            for contact in contacts:
                if contact.updated_at > existing_profile.last_verified_at:
                    is_invalidated = True
                    log.info("Invalidated cached profile: contact has newer updates", contact=contact.full_name)

        if existing_profile and not refresh and not is_invalidated:
            log.info("Returning cached SalesIntelligenceProfile from DB", company=company_obj.name)
            return {
                "success": True,
                "data": self._serialize_profile(existing_profile, str(company_obj.id)),
                "errors": []
            }

        # 3. Fetch Enrichment Data
        enrichment_data = company_obj.enrichment_data or {}
        errors: list[str] = []

        # 4. Synthesize with Modular Engine
        engine = SalesIntelligenceEngine()
        
        log.debug("Synthesizing modular sales intelligence", company=company_obj.name)
        profile_data = await engine.analyze_company(
            company_name=company_obj.name,
            domain=company_obj.domain,
            enrichment_data=enrichment_data
        )

        # 5. Save or update DB
        last_ver = datetime.utcnow()

        if existing_profile:
            for key, value in profile_data.items():
                if hasattr(existing_profile, key):
                    setattr(existing_profile, key, value)
            existing_profile.last_verified_at = last_ver
            session.add(existing_profile)
        else:
            new_profile = SalesIntelligenceProfile(
                company_id=company_obj.id,
                last_verified_at=last_ver
            )
            for key, value in profile_data.items():
                if hasattr(new_profile, key):
                    setattr(new_profile, key, value)
            session.add(new_profile)

        if commit:
            await session.commit()
        else:
            await session.flush()

        profile = existing_profile or new_profile
        
        return {
            "success": True,
            "data": self._serialize_profile(profile, str(company_obj.id)),
            "errors": errors
        }

    def _serialize_profile(self, profile: SalesIntelligenceProfile, company_id: str) -> dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "company_id": company_id,
            "executive_summary": profile.executive_summary,
            "business_overview": profile.business_overview,
            "business_model": profile.business_model,
            "target_customers": profile.target_customers,
            "products_services": profile.products_services,
            "growth_stage": profile.growth_stage,
            "strategic_initiatives": profile.strategic_initiatives,
            "competitive_landscape": profile.competitive_landscape,
            "key_differentiators": profile.key_differentiators,
            "recent_news": profile.recent_news,
            "recent_funding": profile.recent_funding,
            "technology_stack": profile.technology_stack,
            "hiring_activity": profile.hiring_activity,
            "hiring_signals": profile.hiring_signals,
            "buying_signals": profile.buying_signals,
            "digital_transformation_signals": profile.digital_transformation_signals,
            "pain_points": profile.pain_points,
            "product_value_mapping": profile.product_value_mapping,
            "potential_decision_makers": profile.potential_decision_makers,
            "communication_style": profile.communication_style,
            "risk_assessment": profile.risk_assessment,
            "sales_opportunity_summary": profile.sales_opportunity_summary,
            "outreach_intelligence": profile.outreach_intelligence,
            "primary_trigger": profile.primary_trigger,
            "recommended_playbook": profile.recommended_playbook,
            "confidence_score": profile.confidence_score,
            "supporting_sources": profile.supporting_sources,
            "last_verified_at": profile.last_verified_at.isoformat() if profile.last_verified_at else None
        }
