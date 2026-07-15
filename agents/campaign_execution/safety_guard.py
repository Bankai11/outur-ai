"""Campaign Execution Safety Guard."""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.models.outreach_draft import OutreachDraft
from core.models.contact import Contact
from core.models.execution import CampaignDelivery
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

class CampaignSafetyGuard:
    def __init__(self, session: AsyncSession, max_emails_per_run: int = 100, max_emails_per_domain: int = 2):
        self.session = session
        self.max_emails_per_run = max_emails_per_run
        self.max_emails_per_domain = max_emails_per_domain
        
        # Hardcoded for initial release; can be moved to DB or config later
        self.blacklist_domains = {"competitor.com", "fake.com", "test.com", "example.com"}
        self.blacklist_emails = {"donotreply@domain.com", "spam@domain.com"}
        self.allowlist_domains = {"importantclient.com"}
        
    async def evaluate_draft(self, draft: OutreachDraft, contact: Contact, current_run_count: int, domain_counts: dict) -> tuple[bool, str]:
        """
        Evaluates a draft against all safety rules.
        Returns (is_safe, reason).
        """
        # 1. Total emails per run limit
        if current_run_count >= self.max_emails_per_run:
            return False, "Max emails per run limit reached."
            
        domain = contact.email.split("@")[-1].lower() if contact.email else ""
        if not domain:
            return False, "No valid email address."
            
        # 2. Blacklist check
        if domain in self.blacklist_domains or contact.email.lower() in self.blacklist_emails:
            return False, "Contact or domain is blacklisted."
            
        # 3. Domain limit check (bypass if allowlisted)
        if domain not in self.allowlist_domains:
            if domain_counts.get(domain, 0) >= self.max_emails_per_domain:
                return False, f"Max emails per domain ({self.max_emails_per_domain}) reached for {domain}."
                
        # 4. Duplicate delivery check
        stmt = (
            select(func.count())
            .select_from(CampaignDelivery)
            .join(OutreachDraft, CampaignDelivery.draft_id == OutreachDraft.id)
            .where(OutreachDraft.contact_id == contact.id)
            .where(OutreachDraft.campaign_id == draft.campaign_id)
            .where(CampaignDelivery.status.in_(["queued", "sent", "delivered"]))
        )
        res = await self.session.execute(stmt)
        duplicate_count = res.scalar() or 0
        if duplicate_count > 0:
            return False, "Duplicate delivery detected for this contact in this campaign."
            
        return True, "Safe to send."
