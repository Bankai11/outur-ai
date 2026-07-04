import asyncio
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.scout.agent import ScoutAgent
from agents.campaign_manager import generate_outreach_drafts
from core.database import async_session_factory
from core.logger import get_logger
from core.models.campaign import Campaign
from core.models.company import Company
from core.models.contact import Contact
from core.models.outreach_draft import OutreachDraft
from core.services.enrichment.hunter_provider import HunterEnrichmentProvider
from core.services.verification.hunter_verifier import HunterVerificationProvider
from core.services.email import get_email_provider
from datetime import datetime

log = get_logger(__name__)

class AutonomousProspector:
    """
    Autonomous mode orchestrator.
    Loops through the entire lifecycle: Search -> Qualify -> Enrich -> Verify -> Draft -> Send.
    """
    
    def __init__(self):
        self.scout = ScoutAgent()
        self.enricher = HunterEnrichmentProvider()
        self.verifier = HunterVerificationProvider()
        self.email_provider = get_email_provider()
        
    async def run_cycle(self, industry: str = "SaaS", location: str = "Global", limit: int = 5) -> dict[str, Any]:
        """Runs a single autonomous prospecting cycle."""
        log.info("Starting autonomous prospector cycle", industry=industry, location=location)
        
        async with async_session_factory() as session:
            # 1. Ensure we have an Autonomous Campaign
            campaign = await self._get_or_create_campaign(session, industry, location)
            
            # 2. Scout for Companies
            # Run scout (it uses WebSearchProvider if it's in PROVIDERS)
            scout_result = await self.scout.run(industry=industry, location=location, limit=limit, session=session)
            if not scout_result.get("success"):
                log.error("Scout agent failed during autonomous cycle", errors=scout_result.get("errors"))
                return {"success": False, "step": "scout", "errors": scout_result.get("errors")}
                
            companies_data = scout_result.get("data", {}).get("companies", [])
            log.info("Scout discovered companies", count=len(companies_data))
            
            new_contacts = []
            
            # 3. Enrich & Verify
            for comp_data in companies_data:
                company_id = comp_data.get("id")
                domain = comp_data.get("domain")
                if not company_id or not domain:
                    continue
                    
                # Find HR contact
                contact_info = await self.enricher.find_contact(domain, "Talent Acquisition Lead")
                if not contact_info:
                    log.info("No HR contact found", domain=domain)
                    continue
                    
                email = contact_info.get("email")
                if not email:
                    continue
                    
                # Verify Email
                is_valid, verification_details = await self.verifier.verify_email(email)
                
                # STRICT REQUIREMENT: Only verified emails with high confidence
                if not is_valid:
                    log.warning("Email failed verification", email=email, details=verification_details)
                    continue
                    
                # Save Contact
                contact = Contact(
                    company_id=uuid.UUID(company_id),
                    full_name=contact_info.get("full_name", "HR Contact"),
                    job_title=contact_info.get("job_title", "Talent Acquisition"),
                    email=email,
                    linkedin_url=contact_info.get("linkedin_url"),
                    source_url=contact_info.get("source_url"),
                    source_type=contact_info.get("source_type"),
                    retrieved_at=datetime.fromisoformat(contact_info.get("retrieved_at")).replace(tzinfo=None) if contact_info.get("retrieved_at") else datetime.utcnow(),
                    verification_status=verification_details.get("status"),
                    mx_valid=verification_details.get("mx_valid"),
                    confidence_score=verification_details.get("score", contact_info.get("confidence_score", 50))
                )
                session.add(contact)
                await session.flush()
                new_contacts.append(contact)
                
                # Add to Campaign
                selected_contacts = set(campaign.selected_contacts or [])
                selected_contacts.add(str(contact.id))
                campaign.selected_contacts = list(selected_contacts)
                
                selected_companies = set(campaign.selected_companies or [])
                selected_companies.add(company_id)
                campaign.selected_companies = list(selected_companies)
                
            session.add(campaign)
            await session.commit()
            
            if not new_contacts:
                log.info("No new verified contacts discovered in this cycle.")
                return {"success": True, "drafts_generated": 0, "emails_sent": 0}
                
            # 4. Generate Outreach Drafts
            log.info("Generating drafts for new contacts", count=len(new_contacts))
            drafts = await generate_outreach_drafts(campaign.id, session)
            
            # 5. Send Emails
            sent_count = 0
            for draft in drafts:
                if draft.status != "draft" or draft.sent_at:
                    continue
                    
                contact = next((c for c in new_contacts if c.id == draft.contact_id), None)
                if not contact:
                    continue
                    
                result = await self.email_provider.send_email(
                    to_email=contact.email,
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
                    draft.status = "failed"
                    log.error("Failed to send autonomous email", error=result.get("error"))
                    
            await session.commit()
            
            log.info("Autonomous cycle completed", new_contacts=len(new_contacts), emails_sent=sent_count)
            return {
                "success": True,
                "contacts_found": len(new_contacts),
                "drafts_generated": len(drafts),
                "emails_sent": sent_count
            }

    async def _get_or_create_campaign(self, session: AsyncSession, industry: str, location: str) -> Campaign:
        """Finds or creates the autonomous campaign."""
        name = f"Auto Prospecting - {industry} - {location}"
        stmt = select(Campaign).where(Campaign.name == name)
        res = await session.execute(stmt)
        campaign = res.scalar_one_or_none()
        
        if not campaign:
            campaign = Campaign(
                name=name,
                filters={"industry": industry, "location": location, "autonomous": True},
                selected_companies=[],
                selected_contacts=[],
                status="running"
            )
            session.add(campaign)
            await session.commit()
            await session.refresh(campaign)
            
        return campaign
