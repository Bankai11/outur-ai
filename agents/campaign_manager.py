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

from agents.campaign_qa.campaign_qa_engine import CampaignQAEngine
from agents.researcher.sales_intelligence_agent import SalesIntelligenceAgent
from core.config.business_profile import get_business_profile
from core.llm import get_llm_provider
from core.logger import get_logger
from core.models.campaign import Campaign
from core.models.company import Company
from core.models.contact import Contact
from core.models.outreach_draft import OutreachDraft
from core.models.sales_intelligence import SalesIntelligenceProfile
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
    qa_engine = CampaignQAEngine()

    for contact in contacts:
        # Load Company
        company_stmt = select(Company).where(Company.id == contact.company_id)
        company_res = await session.execute(company_stmt)
        company = company_res.scalar_one_or_none()
        if not company:
            continue

        # Load Research Profile (generate on the fly if missing)
        profile_stmt = select(SalesIntelligenceProfile).where(SalesIntelligenceProfile.company_id == company.id)
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()
        if not profile:
            log.info("SalesIntelligenceProfile missing; generating dynamically", company=company.name)
            profile_agent = SalesIntelligenceAgent()
            agent_res = await profile_agent.run(company_id=company.id, session=session)
            if agent_res["success"]:
                profile_res = await session.execute(profile_stmt)
                profile = profile_res.scalar_one_or_none()

        profile_config = get_business_profile()

        # Build personalization context from Outreach Intelligence and Product Mapping
        if profile and profile.outreach_intelligence:
            outreach = profile.outreach_intelligence
            best_opening = outreach.get("best_opening_sentence", "")
            achievement = outreach.get("relevant_achievement", "")
            pain_point = outreach.get("relevant_pain_point", "")
            cta = outreach.get("recommended_cta", "")
            tone = outreach.get("recommended_tone", profile_config.email_tone)
            
            # Fetch Playbook and Trigger context from Sales Intelligence
            primary_trigger = getattr(profile, "primary_trigger", "General Outreach")
            playbook_name = getattr(profile, "recommended_playbook", "General")
            
            # Look up Playbook Details from config
            playbook = next((p for p in profile_config.playbooks if p.name == playbook_name), None)
            playbook_strategy = playbook.messaging_strategy if playbook else "Pitch the product naturally."
            playbook_cta = playbook.cta_style if playbook else "Ask for a quick chat."

            prompt = (
                f"Write a personalized cold email to {contact.full_name} ({contact.job_title}) at {company.name}.\n"
                f"Trigger Event (Why we are emailing them now): {primary_trigger}\n"
                f"Playbook Strategy to follow: {playbook_strategy}\n"
                f"Tone: {tone}\n"
                f"Opening: {best_opening}\n"
                f"Highlight Achievement: {achievement}\n"
                f"Address Pain Point: {pain_point}\n"
                f"Call to Action: {playbook_cta} (Or fallback to: {cta})\n"
                f"CRITICAL RULES:\n"
                f"- Subject Line Rules: {', '.join(profile_config.subject_line_rules)}\n"
                f"- Messaging Guardrails: {', '.join(profile_config.messaging_guardrails)}\n"
                f"- Forbidden Claims: {', '.join(profile_config.forbidden_claims)}\n"
                f"Keep it compelling and tailored to {profile_config.company_name}'s value propositions. Output JSON matching the outreach email schema."
            )
        else:
            primary_trigger = "General Outreach"
            playbook_name = "General Playbook"
            prompt = (
                f"Write a personalized cold email to {contact.full_name} ({contact.job_title}) at {company.name}.\n"
                f"Keep it short, relevant, and compelling. Leverage any available data to pitch {profile_config.company_name}'s {profile_config.product_name}. Output JSON matching the outreach email schema."
            )

        email_data = await llm.generate_json(prompt, EMAIL_SCHEMA)
        if not email_data:
            # Fallback mock template
            subject = f"Streamlining talent pipeline at {company.name}"
            body = (
                f"Hi {contact.full_name},\n\n"
                f"I noticed {company.name} is scaling your operations and managing team growth. "
                f"With your role as {contact.job_title}, I thought Kultrp's culture scaling platform "
                f"could simplify employee onboarding and remote collaboration.\n\n"
                f"Best,\nKultrp team"
            )
        else:
            subject = email_data["subject"]
            body = email_data["body"]
            
        # 1st QA Pass
        qa_report = await qa_engine.evaluate_email(subject, body, contact, company, profile)
        
        # Regeneration logic
        if not qa_report.get("approved"):
            log.info("QA failed, regenerating email once", issues=qa_report.get("issues"))
            issues_str = "\n".join(qa_report.get("issues", []))
            rec_str = "\n".join(qa_report.get("recommendations", []))
            regen_prompt = (
                f"{prompt}\n\n"
                f"Previous attempt was rejected by QA for the following issues:\n{issues_str}\n"
                f"Please apply these recommendations:\n{rec_str}\n"
                f"Do not hallucinate any information. Make it highly personalized and professional."
            )
            email_data_regen = await llm.generate_json(regen_prompt, EMAIL_SCHEMA)
            if email_data_regen:
                subject = email_data_regen["subject"]
                body = email_data_regen["body"]
                
                # 2nd QA Pass
                qa_report = await qa_engine.evaluate_email(subject, body, contact, company, profile)

        # approval_status requires manual intervention now. We just record QA status.
        approval_status = "pending_approval" if qa_report.get("approved") else "rejected"
        qa_score = qa_report.get("overall_score")

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
            existing_draft.approval_status = approval_status
            existing_draft.qa_score = qa_score
            existing_draft.qa_report = qa_report
            existing_draft.primary_trigger = primary_trigger
            existing_draft.playbook_used = playbook_name
            session.add(existing_draft)
            generated_drafts.append(existing_draft)
        else:
            new_draft = OutreachDraft(
                campaign_id=campaign.id,
                contact_id=contact.id,
                subject=subject,
                body=body,
                approval_status=approval_status,
                qa_score=qa_score,
                qa_report=qa_report,
                primary_trigger=primary_trigger,
                playbook_used=playbook_name
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


async def generate_followup_draft(
    campaign_id: uuid.UUID,
    contact_id: uuid.UUID,
    action_type: str,
    session: AsyncSession
) -> OutreachDraft:
    """
    Generate a follow-up outreach email draft for a specific contact using campaign context
    and existing outreach history.
    """
    # 1. Fetch Contact
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFoundError("Contact", contact_id)
        
    # 2. Fetch Company
    company = await session.get(Company, contact.company_id)
    if not company:
        raise NotFoundError("Company", contact.company_id)

    # 3. Fetch Sales Intelligence Profile
    profile_stmt = select(SalesIntelligenceProfile).where(SalesIntelligenceProfile.company_id == company.id)
    profile = (await session.execute(profile_stmt)).scalar_one_or_none()

    # 4. Fetch Previous Outreach Drafts to get thread history
    stmt = select(OutreachDraft).where(
        OutreachDraft.campaign_id == campaign_id,
        OutreachDraft.contact_id == contact_id
    ).order_by(OutreachDraft.created_at.desc())
    prev_drafts = list((await session.execute(stmt)).scalars().all())

    last_subject = ""
    last_body = ""
    if prev_drafts:
        last_subject = prev_drafts[0].subject
        last_body = prev_drafts[0].body

    llm = get_llm_provider()
    
    # 5. Build prompt based on action type
    action_clean = action_type.upper()
    
    instruction = "Write a polite follow-up email."
    if action_clean == "CHANGE_SUBJECT":
        instruction = "Write a follow-up email but use a completely different, more catchy subject line."
    elif action_clean == "CHANGE_TONE":
        instruction = "Write a follow-up email but change the tone to be more direct and casual."
    elif action_clean == "SHORTEN_EMAIL":
        instruction = "Write a follow-up email that is extremely short and concise (under 3 sentences)."
    elif action_clean == "GENERATE_NEW_EMAIL":
        instruction = "Write a completely new outreach email with a fresh angle focusing on a different pain point."

    pain_str = ", ".join([p.get("pain_point", "") for p in profile.pain_points]) if profile else "scaling team"
    news_str = ", ".join([n.get("title", "") for n in profile.recent_news]) if profile else "recent updates"
    
    prompt = (
        f"{instruction}\n"
        f"Recipient: {contact.full_name} ({contact.job_title}) at {company.name}\n"
        f"Previous Subject: {last_subject}\n"
        f"Previous Body: {last_body}\n"
        f"Company News: {news_str}\n"
        f"Pain Points: {pain_str}\n"
        f"Leverage this information to compose the next follow-up. Output JSON matching the outreach email schema."
    )

    email_data = await llm.generate_json(prompt, EMAIL_SCHEMA)
    
    profile_config = get_business_profile()

    if not email_data:
        subject = f"Re: {last_subject}" if last_subject else f"Following up: {profile_config.company_name} x {company.name}"
        body = (
            f"Hi {contact.full_name},\n\n"
            f"Just following up on my previous message. Wanted to see if you had 5 minutes "
            f"this week to chat about optimizing your operations at {company.name}.\n\n"
            f"Best,\n{profile_config.company_name} team"
        )
    else:
        subject = email_data["subject"]
        body = email_data["body"]

    # Save new follow-up draft
    new_draft = OutreachDraft(
        campaign_id=campaign_id,
        contact_id=contact_id,
        subject=subject,
        body=body,
        status="draft"
    )
    session.add(new_draft)
    await session.commit()
    return new_draft

