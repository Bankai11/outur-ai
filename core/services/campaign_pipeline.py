"""
Campaign Pipeline Service

Orchestrates the end-to-end lead generation, contact discovery, lead scoring,
research profiling, outreach drafting, and result-export pipeline.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_factory
from core.logger import configure_logging, get_logger
from core.models.campaign import Campaign
from core.models.contact import Contact
from core.services.export_service import ExportService

if TYPE_CHECKING:
    from agents.researcher.agent import ResearcherAgent
    from agents.researcher.research_profile_agent import ResearchProfileAgent
    from agents.scorer.agent import ScorerAgent
    from agents.scout.agent import ScoutAgent
    from agents.enrichment.agent import EnrichmentAgent

log = get_logger(__name__)


class CampaignPipelineService:
    """Orchestrates the full campaign pipeline by delegating to private step methods.

    Dependencies are injected via the constructor — no DI framework is used.
    """

    def __init__(
        self,
        scout: ScoutAgent,
        researcher: ResearcherAgent,
        enrichment: EnrichmentAgent,
        scorer: ScorerAgent,
        profile_agent: ResearchProfileAgent,
        export_service: ExportService,
    ) -> None:
        self._scout = scout
        self._researcher = researcher
        self._enrichment = enrichment
        self._scorer = scorer
        self._profile_agent = profile_agent
        self._export_service = export_service

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    async def run(
        self,
        industry: str | None,
        country: str | None,
        employees: str | None,
        limit: int,
        output_dir: str,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Execute the full pipeline.

        This is a thin orchestrator that delegates each phase to a dedicated
        private step method.
        """
        configure_logging()
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "outreach_drafts"), exist_ok=True)

        log.info(
            "Starting Campaign Runner Pipeline",
            industry=industry,
            country=country,
            employees=employees,
            limit=limit,
            output_dir=output_dir,
        )

        session_provided = session is not None
        if not session:
            session = async_session_factory()

        try:
            company_ids = await self._discover_companies(
                industry, country, employees, limit, session
            )
            if company_ids is None:
                return {"success": False, "error": "Company discovery failed"}

            await self._discover_contacts(company_ids, session)
            await self._enrich_leads(company_ids, session)
            tier_a_ids = await self._score_leads(company_ids, session)
            await self._generate_research_profiles(tier_a_ids, session)
            campaign_id = await self._generate_outreach_drafts(
                tier_a_ids, industry, country, session
            )
            if campaign_id:
                await self._execute_campaign(campaign_id, session)

            await self._export_results(company_ids, output_dir, session)

            print("[OK] Export completed successfully")
            if not session_provided:
                await session.commit()
            return {"success": True}
        finally:
            if not session_provided:
                await session.close()

    # ------------------------------------------------------------------
    # Private step methods
    # ------------------------------------------------------------------

    async def _discover_companies(
        self,
        industry: str | None,
        country: str | None,
        employees: str | None,
        limit: int,
        session: AsyncSession,
    ) -> list[str] | None:
        """Step 1 — Discover target companies via ScoutAgent.

        Returns a list of company UUID strings on success, or ``None`` if
        company discovery fails.
        """
        print("Discovering companies...")
        scout_res = await self._scout.run(
            industry=industry,
            location=country,
            company_size=employees,
            limit=limit,
            session=session,
        )

        if not scout_res["success"]:
            print(f"[ERROR] Company discovery failed: {', '.join(scout_res['errors'])}")
            return None

        discovered = scout_res["data"]["companies"]
        print(f"[OK] {len(discovered)} companies found")
        return [c["id"] for c in discovered]

    async def _discover_contacts(
        self,
        company_ids: list[str],
        session: AsyncSession,
    ) -> int:
        """Step 2 — Discover contacts for each company via ResearcherAgent.

        Continues processing when an individual company fails (error isolation).
        Returns the total number of contacts found.
        """
        print("\nFinding contacts...")
        total = 0

        for co_id in company_ids:
            try:
                res = await self._researcher.run(company_id=co_id, session=session)
                if res["success"]:
                    total += len(res["data"]["contacts"])
            except Exception as exc:
                log.error(
                    "Failed discovering contacts for company",
                    company_id=co_id,
                    error=str(exc),
                )
                continue

        print(f"[OK] {total} contacts found")
        return total

    async def _enrich_leads(
        self,
        company_ids: list[str],
        session: AsyncSession,
    ) -> None:
        """Step 2.5 — Enrich each company and its contacts via EnrichmentAgent."""
        print("\nEnriching leads...")
        
        for co_id in company_ids:
            try:
                res = await self._enrichment.run(company_id=co_id, session=session)
                if not res["success"]:
                    log.warning(
                        "Enrichment partially failed or returned no data",
                        company_id=co_id,
                        errors=res.get("errors")
                    )
            except Exception as exc:
                log.error("Failed to enrich company", company_id=co_id, error=str(exc))
                continue
                
        print(f"[OK] Enrichment complete for {len(company_ids)} companies")

    async def _score_leads(
        self,
        company_ids: list[str],
        session: AsyncSession,
    ) -> list[str]:
        """Step 3 — Score each company and collect Tier-A IDs via ScorerAgent.

        Returns the list of company UUID strings that received Tier-A ranking.
        """
        print("\nScoring leads...")
        tier_a_ids: list[str] = []

        for co_id in company_ids:
            try:
                score_res = await self._scorer.run(company_id=co_id, session=session)
                if score_res["success"] and score_res["data"]["tier"] == "A":
                    tier_a_ids.append(co_id)
            except Exception as exc:
                log.error("Failed scoring company", company_id=co_id, error=str(exc))
                continue

        print(f"[OK] {len(tier_a_ids)} Tier A leads")
        return tier_a_ids

    async def _generate_research_profiles(
        self,
        tier_a_company_ids: list[str],
        session: AsyncSession,
    ) -> None:
        """Step 4 — Generate research profiles for Tier-A companies."""
        print("\nGenerating research...")

        for co_id in tier_a_company_ids:
            try:
                await self._profile_agent.run(company_id=co_id, session=session)
            except Exception as exc:
                log.error(
                    "Failed generating research profile",
                    company_id=co_id,
                    error=str(exc),
                )
                continue

        print("[OK] Complete")

    async def _generate_outreach_drafts(
        self,
        tier_a_company_ids: list[str],
        industry: str | None,
        country: str | None,
        session: AsyncSession,
    ) -> uuid.UUID | None:
        """Step 5 — Create a Campaign and generate outreach drafts for Tier-A contacts.

        Returns the campaign ID if created.
        """
        print("\nGenerating outreach...")

        tier_a_uuids = [uuid.UUID(co_id) for co_id in tier_a_company_ids]

        contact_stmt = select(Contact).where(Contact.company_id.in_(tier_a_uuids))
        contact_res = await session.execute(contact_stmt)
        tier_a_contacts = list(contact_res.scalars().all())
        tier_a_contact_ids = [str(c.id) for c in tier_a_contacts]

        drafts_count = 0
        if tier_a_contact_ids:
            camp_name = (
                f"CLI Campaign {industry or ''} {country or ''} "
                f"{datetime.now(UTC).strftime('%Y%m%d%H%M')}"
            )
            campaign = Campaign(
                name=camp_name,
                selected_companies=tier_a_company_ids,
                selected_contacts=tier_a_contact_ids,
                status="draft",
            )
            session.add(campaign)
            await session.commit()

            try:
                from agents.campaign_manager import generate_outreach_drafts

                drafts = await generate_outreach_drafts(
                    campaign_id=campaign.id, session=session
                )
                drafts_count = len(drafts)
            except Exception as exc:
                log.error(
                    "Failed generating campaign outreach drafts",
                    campaign_id=campaign.id,
                    error=str(exc),
                )

        print(f"[OK] {drafts_count} drafts created")
        return campaign.id if tier_a_contact_ids else None

    async def _execute_campaign(self, campaign_id: uuid.UUID, session: AsyncSession) -> None:
        """Step 5.5 - Execute the campaign delivery via CampaignExecutor."""
        print("\nExecuting campaign delivery (enqueuing jobs)...")
        from agents.campaign_execution.executor import CampaignExecutor
        from agents.campaign_execution.models import ProviderConfig
        
        # Configure a mock provider for this pipeline run
        config = ProviderConfig(
            provider_name="mock_provider",
            rate_limit_per_minute=100
        )
        executor = CampaignExecutor(provider_config=config)
        
        try:
            run_id = await executor.execute_campaign(campaign_id)
            print(f"[OK] Campaign execution started. Run ID: {run_id}")
        except Exception as exc:
            log.error("Failed to execute campaign", campaign_id=campaign_id, error=str(exc))

    async def _export_results(
        self,
        company_ids: list[str],
        output_dir: str,
        session: AsyncSession,
    ) -> None:
        """Step 6 — Export all pipeline results to CSV / JSON files."""
        print(f"\nExporting results to {output_dir}...")
        await self._export_service.export_all(
            company_ids=company_ids,
            output_dir=output_dir,
            session=session,
        )
