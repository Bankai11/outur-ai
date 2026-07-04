#!/usr/bin/env python3
"""
Outur AI Campaign Runner CLI Tool

Orchestrates lead generation, contact discovery, lead scoring, research profiling,
and outreach drafting into a single end-to-end command-line workflow.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Configure path so local modules import correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import async_session_factory, engine
from core.logger import configure_logging, get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.models.research_profile import ResearchProfile
from core.models.campaign import Campaign
from core.models.outreach_draft import OutreachDraft
from agents.scout.agent import ScoutAgent
from agents.researcher.agent import ResearcherAgent
from agents.scorer.agent import ScorerAgent
from agents.researcher.research_profile_agent import ResearchProfileAgent
from agents.campaign_manager import generate_outreach_drafts

log = get_logger(__name__)


async def run_pipeline(
    industry: str | None,
    country: str | None,
    employees: str | None,
    limit: int,
    output_dir: str,
    session: AsyncSession | None = None
) -> dict[str, Any]:
    """
    Executes the end-to-end campaign runner pipeline.
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
        output_dir=output_dir
    )

    session_provided = session is not None
    if not session:
        session = async_session_factory()

    try:
        # Step 1: Discover companies
        print("Discovering companies...")
        scout = ScoutAgent()
        scout_res = await scout.run(
            industry=industry,
            location=country,
            company_size=employees,
            limit=limit,
            session=session
        )
        
        if not scout_res["success"]:
            print(f"[ERROR] Company discovery failed: {', '.join(scout_res['errors'])}")
            return {"success": False, "error": "Company discovery failed"}

        discovered_companies = scout_res["data"]["companies"]
        print(f"[OK] {len(discovered_companies)} companies found")

        company_ids = [c["id"] for c in discovered_companies]
        
        # Step 2: Discover contacts
        print("\nFinding contacts...")
        researcher = ResearcherAgent()
        total_contacts_count = 0
        
        for co_id in company_ids:
            try:
                res_contacts = await researcher.run(company_id=co_id, session=session)
                if res_contacts["success"]:
                    total_contacts_count += len(res_contacts["data"]["contacts"])
            except Exception as e:
                log.error("Failed discovering contacts for company", company_id=co_id, error=str(e))
                # Continue processing even if one company fails
                continue
        
        print(f"[OK] {total_contacts_count} contacts found")

        # Step 3: Scoring leads
        print("\nScoring leads...")
        scorer = ScorerAgent()
        tier_a_company_ids = []

        for co_id in company_ids:
            try:
                score_res = await scorer.run(company_id=co_id, session=session)
                if score_res["success"] and score_res["data"]["tier"] == "A":
                    tier_a_company_ids.append(co_id)
            except Exception as e:
                log.error("Failed scoring company", company_id=co_id, error=str(e))
                continue

        print(f"[OK] {len(tier_a_company_ids)} Tier A leads")

        # Step 4: Generating research profiles for Tier A leads
        print("\nGenerating research...")
        profile_agent = ResearchProfileAgent()
        
        for co_id in tier_a_company_ids:
            try:
                await profile_agent.run(company_id=co_id, session=session)
            except Exception as e:
                log.error("Failed generating research profile", company_id=co_id, error=str(e))
                continue

        print("[OK] Complete")

        # Step 5: Generating outreach drafts for Tier A contacts
        print("\nGenerating outreach...")
        
        # Resolve all contacts associated with Tier A companies
        tier_a_uuids = [uuid.UUID(co_id) for co_id in tier_a_company_ids]
        
        contact_stmt = select(Contact).where(Contact.company_id.in_(tier_a_uuids))
        contact_res = await session.execute(contact_stmt)
        tier_a_contacts = list(contact_res.scalars().all())
        tier_a_contact_ids = [str(c.id) for c in tier_a_contacts]

        drafts_count = 0
        if tier_a_contact_ids:
            # Create a Campaign to target these contacts
            camp_name = f"CLI Campaign {industry or ''} {country or ''} {datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
            campaign = Campaign(
                name=camp_name,
                selected_companies=tier_a_company_ids,
                selected_contacts=tier_a_contact_ids,
                status="draft"
            )
            session.add(campaign)
            await session.commit()
            
            try:
                drafts = await generate_outreach_drafts(campaign_id=campaign.id, session=session)
                drafts_count = len(drafts)
            except Exception as e:
                log.error("Failed generating campaign outreach drafts", campaign_id=campaign.id, error=str(e))
        
        print(f"[OK] {drafts_count} drafts created")

        # Step 6: Export Results to CSV/JSON files
        print(f"\nExporting results to {output_dir}...")
        
        # Query all discovered companies from DB to get their ORM models
        co_uuids = [uuid.UUID(cid) for cid in company_ids]
        co_stmt = select(Company).where(Company.id.in_(co_uuids))
        co_res = await session.execute(co_stmt)
        companies_list = list(co_res.scalars().all())

        # Write companies.csv
        with open(os.path.join(output_dir, "companies.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Website", "Domain", "Industry", "Location", "Source", "Score", "Tier"])
            for co in companies_list:
                writer.writerow([co.id, co.name, co.website, co.domain, co.industry, co.location, co.source, co.score, co.tier])

        # Write contacts.csv
        con_stmt = select(Contact).where(Contact.company_id.in_(co_uuids))
        con_res = await session.execute(con_stmt)
        contacts_list = list(con_res.scalars().all())
        
        with open(os.path.join(output_dir, "contacts.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Company ID", "Full Name", "Job Title", "Email", "LinkedIn URL", "Confidence Score"])
            for c in contacts_list:
                writer.writerow([c.id, c.company_id, c.full_name, c.job_title, c.email, c.linkedin_url, c.confidence_score])

        # Write tier_a.csv
        tier_a_companies = [co for co in companies_list if co.tier == "A"]
        with open(os.path.join(output_dir, "tier_a.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Website", "Domain", "Industry", "Score"])
            for co in tier_a_companies:
                writer.writerow([co.id, co.name, co.website, co.domain, co.industry, co.score])

        # Write research_profiles.json
        profiles_stmt = select(ResearchProfile).where(ResearchProfile.company_id.in_(co_uuids))
        profiles_res = await session.execute(profiles_stmt)
        profiles_list = list(profiles_res.scalars().all())
        
        profiles_json = []
        for p in profiles_list:
            profiles_json.append({
                "company_id": str(p.company_id),
                "summary": p.summary,
                "hiring_signals": p.hiring_signals,
                "growth_indicators": p.growth_indicators,
                "public_pain_points": p.public_pain_points,
                "why_now": p.why_now,
                "recommended_pitch": p.recommended_pitch,
                "best_contact": p.best_contact,
                "outreach_angles": p.outreach_angles,
                "next_recommended_action": p.next_recommended_action,
                "llm_confidence": p.llm_confidence,
                "data_quality": p.data_quality,
                "freshness_score": p.freshness_score
            })
            
        with open(os.path.join(output_dir, "research_profiles.json"), "w", encoding="utf-8") as f:
            json.dump(profiles_json, f, indent=2)

        # Write individual outreach drafts files
        drafts_stmt = select(OutreachDraft)
        drafts_res = await session.execute(drafts_stmt)
        all_drafts = list(drafts_res.scalars().all())
        
        contacts_map = {c.id: c for c in contacts_list}
        
        for d in all_drafts:
            c = contacts_map.get(d.contact_id)
            c_name = c.full_name.replace(" ", "_") if c else str(d.contact_id)
            draft_filepath = os.path.join(output_dir, "outreach_drafts", f"draft_{c_name}.txt")
            
            with open(draft_filepath, "w", encoding="utf-8") as f:
                f.write(f"Subject: {d.subject}\n")
                f.write(f"To: {c.email if c else ''}\n")
                f.write("=" * 60 + "\n")
                f.write(d.body)

        print("[OK] Export completed successfully")
        if not session_provided:
            await session.commit()
        return {"success": True}
    finally:
        if not session_provided:
            await session.close()


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Outur AI end-to-end Campaign Runner CLI.")
    parser.add_argument("--industry", type=str, help="Target company industry filters")
    parser.add_argument("--country", type=str, help="Target location/country filters")
    parser.add_argument("--employees", type=str, help="Target headcount size range filters")
    parser.add_argument("--limit", type=int, default=5, help="Limit of companies discovered")
    parser.add_argument("--output", type=str, default="exports", help="Directory where CSV/JSON files are exported")

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        res = loop.run_until_complete(
            run_pipeline(
                industry=args.industry,
                country=args.country,
                employees=args.employees,
                limit=args.limit,
                output_dir=args.output
            )
        )
        if not res.get("success"):
            sys.exit(1)
    finally:
        # Dispose of engine connection pool on exit
        loop.run_until_complete(engine.dispose())


if __name__ == "__main__":
    main()
