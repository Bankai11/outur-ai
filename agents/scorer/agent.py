"""
Scorer Agent

Calculates a lead score from 0 to 100 for a company based on:
- Industry fit
- Company size (deterministic mock/enriched)
- Recent growth (deterministic mock/enriched)
- Hiring activity (careers page or source)
- HR team size (number of contacts discovered)
- Availability of contact information (emails, linkedin URLs)
Saves score, tier, and signals to the Company database table.
"""

from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_factory
from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.utils.exceptions import NotFoundError

log = get_logger(__name__)


class ScorerAgent:
    """
    Agent responsible for prioritising companies based on fit and contact availability.
    """

    agent_name: str = "scorer"

    def __init__(self) -> None:
        log.debug("ScorerAgent initialised", agent=self.agent_name)

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Scorer Agent.

        Parameters
        ----------
        company_id: str | uuid.UUID | None
            The ID of the company to score.
        company: Company | None
            An already loaded Company object.
        session: AsyncSession | None
            Optional database session.
        """
        log.info("Running Scorer Agent", inputs=list(kwargs.keys()))

        company_id = kwargs.get("company_id")
        company = kwargs.get("company")
        session_param = kwargs.get("session")

        try:
            if isinstance(session_param, AsyncSession):
                # Use standard provided session
                result = await self._execute_agent(
                    company_id=company_id,
                    company=company,
                    session=session_param,
                    commit=False
                )
            else:
                # Open a new transaction
                async with async_session_factory() as local_session:
                    try:
                        result = await self._execute_agent(
                            company_id=company_id,
                            company=company,
                            session=local_session,
                            commit=True
                        )
                    except Exception:
                        await local_session.rollback()
                        raise
            return result
        except NotFoundError as e:
            log.error("Company not found during scoring", error=e.detail)
            return {
                "success": False,
                "data": {},
                "errors": [e.detail]
            }
        except Exception as e:
            log.error("Failed to run Scorer Agent", error=str(e))
            return {
                "success": False,
                "data": {},
                "errors": [str(e)]
            }

    async def _execute_agent(
        self,
        company_id: Any,
        company: Any,
        session: AsyncSession,
        commit: bool = True
    ) -> dict[str, Any]:
        # 1. Resolve Company record
        company_obj: Company | None = None
        if company and isinstance(company, Company):
            company_obj = company
        elif company_id:
            # Parse UUID safely
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

        # 2. Extract context details
        slug = (company_obj.domain or company_obj.name).lower()
        # Generate deterministic mock growth & size metrics based on company name hash
        h = hash(slug)
        size = 10 + (abs(h) % 490)       # 10 to 500 headcount
        growth = 1 + (abs(h) % 49)       # 1% to 50% growth

        # Fetch contacts explicitly
        contacts_stmt = select(Contact).where(Contact.company_id == company_obj.id)
        contacts_res = await session.execute(contacts_stmt)
        contacts = list(contacts_res.scalars().all())
        contact_count = len(contacts)
        has_emails = any(c.email for c in contacts)
        has_linkedin = any(c.linkedin_url for c in contacts)

        # 3. Calculate Scores
        signals: list[str] = []
        score = 0

        # Industry Fit (Max 20 pts)
        ind_fit_list = {"saas", "fintech", "tech", "ai", "healthtech", "biotech"}
        company_ind = (company_obj.industry or "").lower()
        if any(fit in company_ind for fit in ind_fit_list):
            score += 20
            signals.append("industry_fit")
        elif company_ind:
            score += 12
        else:
            score += 8

        # Company Size (Max 15 pts)
        if 50 <= size <= 250:
            score += 15
            signals.append("icp_size_sweetspot")
        elif size > 250:
            score += 10
        else:
            score += 5

        # Recent Growth (Max 15 pts)
        if growth >= 20:
            score += 15
            signals.append("high_growth")
        elif growth >= 10:
            score += 10
        else:
            score += 5

        # Hiring Activity (Max 20 pts)
        if company_obj.careers_page or company_obj.source == "job_board":
            score += 20
            signals.append("active_hiring")
        else:
            score += 8

        # HR Team Size / Contacts Discovered (Max 15 pts)
        if contact_count >= 3:
            score += 15
            signals.append("large_hr_team")
        elif contact_count > 0:
            score += 10
            signals.append("contacts_found")
        else:
            score += 2

        # Availability of Contact Info (Max 15 pts)
        info_pts = 0
        if has_emails:
            info_pts += 8
        if has_linkedin:
            info_pts += 7
        if info_pts > 0:
            score += info_pts
            signals.append("contact_info_available")

        # Clamp score between 0 and 100
        score = max(0, min(100, score))

        # Assign Tier
        if score >= 80:
            tier = "A"
        elif score >= 50:
            tier = "B"
        else:
            tier = "C"

        # 4. Save to Company record
        company_obj.score = score
        company_obj.tier = tier
        company_obj.score_signals = signals
        session.add(company_obj)

        if commit:
            await session.commit()
        else:
            await session.flush()

        log.info(
            "Scored company lead successfully",
            company=company_obj.name,
            score=score,
            tier=tier,
            signals=signals
        )

        return {
            "success": True,
            "data": {
                "company_id": str(company_obj.id),
                "score": score,
                "tier": tier,
                "signals": signals
            },
            "errors": []
        }
