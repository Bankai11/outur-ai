"""
Campaign Manager Service Logic

Handles generating personalized cold outreach drafts for target contacts using
company research profiles, and exports them to CSV, Gmail Draft MIME, and Outlook REST API formats.
"""

from __future__ import annotations

import base64
from email.message import EmailMessage
import io
import json
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.researcher.research_profile_agent import ResearchProfileAgent
from core.llm import get_llm_provider
from core.logger import get_logger
from core.models.campaign import Campaign
from core.models.company import Company
from core.models.contact import Contact
from core.models.outreach_draft import OutreachDraft
from core.models.research_profile import ResearchProfile
from core.utils.exceptions import NotFoundError, ValidationError

log = get_logger(__name__)

EMAIL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "subject": {"type": "STRING", "description": "Subject line for the outreach cold email."},
        "body": {"type": "STRING", "description": "Body content for the outreach cold email."}
    },
    "required": ["subject", "body"]
}


async def generate_outreach_drafts(
    campaign_id: uuid.UUID,
    session: AsyncSession
) -> list[OutreachDraft]:
    """
    Generate cold outreach email drafts for all selected contacts in a campaign.
    """
    # 1. Fetch Campaign
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    res = await session.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise NotFoundError("Campaign", campaign_id)

    log.info("Generating drafts for campaign", campaign_name=campaign.name)

    # 2. Load contacts
    contact_ids = [uuid.UUID(cid) for cid in campaign.selected_contacts]
    if not contact_ids:
        raise ValidationError("Campaign has no selected contacts to generate drafts for.")

    contact_stmt = select(Contact).where(Contact.id.in_(contact_ids))
    contact_res = await session.execute(contact_stmt)
    contacts = list(contact_res.scalars().all())

    # Map contacts to their companies and generate drafts
    generated_drafts = []
    llm = get_llm_provider()

    for contact in contacts:
        # Load Company
        company_stmt = select(Company).where(Company.id == contact.company_id)
        company_res = await session.execute(company_stmt)
        company = company_res.scalar_one_or_none()
        if not company:
            continue

        # Load Research Profile (generate on the fly if missing)
        profile_stmt = select(ResearchProfile).where(ResearchProfile.company_id == company.id)
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()
        if not profile:
            log.info("ResearchProfile missing; generating dynamically", company=company.name)
            profile_agent = ResearchProfileAgent()
            agent_res = await profile_agent.run(company_id=company.id, session=session)
            if agent_res["success"]:
                profile_res = await session.execute(profile_stmt)
                profile = profile_res.scalar_one_or_none()

        # Opportunity Score Gate (Phase 7 Autonomy)
        if profile and profile.opportunity_score < 70:
            log.info("Skipping draft generation due to low opportunity score", company=company.name, score=profile.opportunity_score)
            continue

        # Build personalization context
        why_now_analysis = profile.raw_evidence.get("why_now_analysis", {}) if profile else {}
        why_now_summary = why_now_analysis.get("summary", "Fast-growing market player.")
        chain_of_reasoning = why_now_analysis.get("chain_of_reasoning", [])
        pain_str = ", ".join([p.get("insight", "") for p in profile.public_pain_points]) if profile else "scaling team"
        hiring_str = ", ".join([h.get("insight", "") for h in profile.hiring_signals]) if profile else "hiring engineers"
        news_str = ", ".join([n.get("title", "") for n in profile.recent_news]) if profile else "recent updates"
        opportunity_score = profile.opportunity_score if profile else 50
        why_now_score = profile.why_now_score if profile else 50

        prompt = (
            f"Write a personalized cold email to {contact.full_name} ({contact.job_title}) at {company.name}.\n"
            f"Company Context (Why Now): {why_now_summary}\n"
            f"Reasoning Chain: {' -> '.join(chain_of_reasoning)}\n"
            f"Hiring Signals: {hiring_str}\n"
            f"Recent News: {news_str}\n"
            f"Identified Pain Points: {pain_str}\n"
            f"Opportunity Score: {opportunity_score}/100, Why Now Score: {why_now_score}/100\n"
            f"Keep it short, relevant, and compelling. Leverage the 'Why Now' reasoning to pitch Outur AI's automated recruitment agents. Output JSON matching the outreach email schema."
        )

        email_data = await llm.generate_json(prompt, EMAIL_SCHEMA)
        if not email_data:
            # Fallback mock template
            subject = f"Streamlining talent pipeline at {company.name}"
            body = (
                f"Hi {contact.full_name},\n\n"
                f"I noticed {company.name} is scaling your operations and managing team growth. "
                f"With your role as {contact.job_title}, I thought Outur AI's automated recruitment agents "
                f"could simplify candidate matches to resolve backend scaling paint points.\n\n"
                f"Best,\nOutur AI team"
            )
        else:
            subject = email_data["subject"]
            body = email_data["body"]

        # Check if draft already exists to avoid duplicates
        existing_stmt = select(OutreachDraft).where(
            (OutreachDraft.campaign_id == campaign.id) &
            (OutreachDraft.contact_id == contact.id)
        )
        existing_res = await session.execute(existing_stmt)
        existing_draft = existing_res.scalar_one_or_none()

        if existing_draft:
            existing_draft.subject = subject
            existing_draft.body = body
            session.add(existing_draft)
            generated_drafts.append(existing_draft)
        else:
            new_draft = OutreachDraft(
                campaign_id=campaign.id,
                contact_id=contact.id,
                subject=subject,
                body=body
            )
            session.add(new_draft)
            generated_drafts.append(new_draft)

    campaign.status = "generated"
    session.add(campaign)
    await session.commit()

    return generated_drafts


async def export_campaign_drafts(
    campaign_id: uuid.UUID,
    export_format: str,
    session: AsyncSession
) -> Any:
    """
    Export cold outreach email drafts for a campaign into various formats.
    """
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    res = await session.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise NotFoundError("Campaign", campaign_id)

    drafts_stmt = select(OutreachDraft).where(OutreachDraft.campaign_id == campaign.id)
    drafts_res = await session.execute(drafts_stmt)
    drafts = list(drafts_res.scalars().all())

    if not drafts:
        raise ValidationError("Campaign has no generated outreach drafts to export. Call generate first.")

    # We need contact details for mapping emails/names
    contact_ids = [d.contact_id for d in drafts]
    contact_stmt = select(Contact).where(Contact.id.in_(contact_ids))
    contact_res = await session.execute(contact_stmt)
    contacts_map = {c.id: c for c in contact_res.scalars().all()}

    # We also need company names
    company_stmt = select(Company).where(Company.id.in_([c.company_id for c in contacts_map.values()]))
    company_res = await session.execute(company_stmt)
    companies_map = {co.id: co for co in company_res.scalars().all()}

    format_clean = export_format.strip().lower()

    if format_clean == "csv":
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Contact Name", "Email", "Company", "Subject", "Body"])
        for d in drafts:
            c = contacts_map.get(d.contact_id)
            c_name = c.full_name if c else ""
            c_email = c.email if c else ""
            co = companies_map.get(c.company_id) if c else None
            co_name = co.name if co else ""
            writer.writerow([c_name, c_email, co_name, d.subject, d.body])
        return output.getvalue()

    elif format_clean == "gmail_draft":
        gmail_payloads = []
        for d in drafts:
            c = contacts_map.get(d.contact_id)
            c_email = c.email if c else "recipient@company.com"
            
            # Formulate raw MIME RFC 822 email message
            mime_msg = EmailMessage()
            mime_msg["To"] = c_email
            mime_msg["Subject"] = d.subject
            mime_msg.set_content(d.body)
            
            # Base64url encode the MIME payload as required by Google APIs
            raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes())
            raw_str = raw_bytes.decode("utf-8")
            gmail_payloads.append({"message": {"raw": raw_str}})
        return gmail_payloads

    elif format_clean == "outlook_draft":
        outlook_payloads = []
        for d in drafts:
            c = contacts_map.get(d.contact_id)
            c_email = c.email if c else "recipient@company.com"
            outlook_payloads.append({
                "subject": d.subject,
                "body": {
                    "contentType": "Text",
                    "content": d.body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": c_email
                        }
                    }
                ]
            })
        return outlook_payloads

    else:
        raise ValidationError(f"Unsupported export format '{export_format}'. Supported formats: csv, gmail_draft, outlook_draft.")
