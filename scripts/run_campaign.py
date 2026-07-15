import asyncio
import uuid
import sys
import os
import argparse
import logging
from typing import List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database.engine import async_session_factory
from core.models.campaign import Campaign
from core.models.contact import Contact
from agents.icp_discovery.discovery_agent import ICPDiscoveryAgent
from agents.icp_discovery.schema import CampaignRequirements
from agents.scout.agent import ScoutAgent
from agents.researcher.agent import ResearcherAgent
from agents.campaign_manager import generate_outreach_drafts
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("campaign_run")

ARTIFACT_PATH = r"C:\Users\banka\.gemini\antigravity-ide\brain\8742f29c-8d30-481e-a3e0-49863bb70ca6\generated_emails.md"
REPORT_PATH = r"C:\Users\banka\.gemini\antigravity-ide\brain\8742f29c-8d30-481e-a3e0-49863bb70ca6\execution_report.md"

def verify_providers():
    log.info("Running pre-flight checks...")
    from core.config.settings import get_settings
    settings = get_settings()
    
    missing = []
    if not settings.gemini_api_key or settings.gemini_api_key == "CHANGE_ME":
        missing.append("GEMINI_API_KEY")
    if not settings.tavily_api_key:
        missing.append("TAVILY_API_KEY")
        
    if missing:
        log.error(f"Provider Verification Failed! Missing required configuration: {', '.join(missing)}")
        log.error("Please add them to your .env file or environment.")
        sys.exit(1)
    
    log.info("Pre-flight checks passed.")

async def main():
    parser = argparse.ArgumentParser(description="Run Outbound Acquisition Campaign.")
    parser.add_argument("--dry-run", action="store_true", help="Stop before attempting any live sending. Generate report only.")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip discovery and use an existing campaign (requires --campaign-id)")
    parser.add_argument("--campaign-id", type=str, help="Existing Campaign ID to process")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of prospects generated.")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of companies to process per batch.")
    args = parser.parse_args()

    verify_providers()
    from core.config.business_profile import get_business_profile
    profile = get_business_profile()

    async with async_session_factory() as session:
        # 1. Create Campaign
        campaign_id = uuid.uuid4()
        campaign = Campaign(
            id=campaign_id,
            name=f"{profile.company_name} Initial Acquisition",
            filters={
                "industry": "SaaS, Technology, IT Services, Healthcare",
                "employee_range": "50-500",
                "keywords": ["remote-first", "hybrid", "fast-growing", "scaling", "hiring"],
                "min_icp_score": 75
            },
            status="draft",
            selected_companies=[],
            selected_contacts=[]
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)
        log.info(f"Created campaign: {campaign.id}")

        # 2. Discover Prospects
        log.info(f"Starting ICP Discovery for {args.limit} prospects...")
        reqs = CampaignRequirements(**campaign.filters)
        discovery = ICPDiscoveryAgent()
        
        ranked = await discovery.discover_and_rank(reqs, limit=args.limit)
        
        companies_list = []
        for rc in ranked:
            companies_list.append({
                "name": rc.company_name,
                "website": rc.website,
                "industry": rc.industry,
                "location": rc.country,
                "source": "icp_discovery"
            })
            
        log.info(f"Discovered {len(companies_list)} prospects.")

        if not companies_list:
            log.error("No companies discovered. Aborting.")
            return

        # 3. Save Prospects via ScoutAgent
        log.info("Saving prospects to DB via ScoutAgent...")
        scout = ScoutAgent()
        scout_res = await scout.run(companies_list=companies_list, session=session, limit=args.limit)
        saved_companies = scout_res.get("data", {}).get("companies", [])
        log.info(f"Saved {len(saved_companies)} companies.")

        # Assign to campaign
        c_ids = [c["id"] for c in saved_companies]
        campaign.selected_companies = c_ids
        
        # 4. Find Contacts via ResearcherAgent
        log.info("Finding contacts via ResearcherAgent...")
        researcher = ResearcherAgent()
        contact_ids = []
        
        batch_size = args.batch_size
        for batch_start in range(0, len(c_ids), batch_size):
            batch_c_ids = c_ids[batch_start:batch_start + batch_size]
            log.info(f"Processing batch {batch_start//batch_size + 1} ({len(batch_c_ids)} companies)...")
            
            for idx, c_id in enumerate(batch_c_ids):
                real_idx = batch_start + idx + 1
                log.info(f"Researching company {real_idx}/{len(c_ids)}...")
                res = await researcher.run(company_id=c_id, session=session)
                found_contacts = res.get("data", {}).get("contacts", [])
                if found_contacts:
                    # Pick the first contact
                    contact_ids.append(found_contacts[0]["id"])
                    
            campaign.selected_contacts = [str(cid) for cid in contact_ids]
            session.add(campaign)
            await session.commit()
            
            if batch_start + batch_size < len(c_ids):
                log.info("Taking a 5s breather before the next batch...")
                await asyncio.sleep(5.0)
        
        log.info(f"Found and linked {len(contact_ids)} contacts to campaign.")

        if not contact_ids:
            log.error("No contacts found. Aborting.")
            return

        # 5. Generate Drafts (triggers Sales Intel + QA automatically)
        log.info("Generating outreach drafts...")
        drafts = await generate_outreach_drafts(campaign.id, session)
        log.info(f"Generated {len(drafts)} email drafts.")
        
        # Calculate stats for the report
        total_companies = len(companies_list)
        qualified_companies = len(c_ids)
        total_contacts = len(contact_ids)
        
        qa_scores = [d.qa_score for d in drafts if d.qa_score is not None]
        avg_qa_score = sum(qa_scores) / len(qa_scores) if qa_scores else 0.0

        # Generate Execution Report
        log.info(f"Writing execution report to {REPORT_PATH}")
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("# Campaign Execution Report\n\n")
            f.write(f"**Campaign ID**: `{campaign.id}`\n")
            f.write(f"**Mode**: {'DRY RUN' if args.dry_run else 'LIVE'}\n\n")
            
            f.write("## Overview\n")
            f.write(f"- Total companies discovered: {total_companies}\n")
            f.write(f"- Qualified companies: {qualified_companies}\n")
            f.write(f"- Contacts found: {total_contacts}\n")
            f.write(f"- Average QA Score: {avg_qa_score:.2f}\n")
            f.write(f"- Drafts generated: {len(drafts)}\n\n")
            
            f.write("## Drafts (Pending Approval)\n")
            for d in drafts:
                c_stmt = select(Contact).where(Contact.id == d.contact_id)
                c_res = await session.execute(c_stmt)
                contact = c_res.scalar_one_or_none()
                name = contact.full_name if contact else str(d.contact_id)
                
                f.write(f"### {name}\n")
                f.write(f"- **Draft ID**: `{d.id}`\n")
                f.write(f"- **QA Status**: {d.qa_report.get('approved', False) if d.qa_report else False}\n")
                f.write(f"- **QA Score**: {d.qa_score}\n")
                f.write(f"- **Subject**: {d.subject}\n\n")
                f.write(f"```text\n{d.body}\n```\n\n")

        if args.dry_run:
            log.info("Dry run complete. No emails were queued. Review the report and use the approve script.")
        else:
            log.info("Live run specified. Attempting to execute campaign...")
            # Note: Executor only sends "approved" drafts. Since drafts are "pending_approval", 
            # this run will likely queue 0 emails unless they were manually approved. 
            # We run it anyway in case they are running this script again with --skip-discovery on an approved campaign.
            from agents.campaign_execution.executor import CampaignExecutor
            from agents.campaign_execution.models import ProviderConfig
            # Provide a dummy provider config for now since we aren't fully wired to Resend yet
            config = ProviderConfig(provider_name="console", api_key="test")
            executor = CampaignExecutor(provider_config=config)
            run_id = await executor.execute_campaign(campaign.id)
            log.info(f"Campaign execution run completed with run_id: {run_id}")
                
        log.info("Done!")

if __name__ == "__main__":
    asyncio.run(main())
