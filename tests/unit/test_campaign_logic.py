"""Unit tests for Campaign Manager service logic and exporters."""

from __future__ import annotations

import base64
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.campaign_manager import generate_outreach_drafts, export_campaign_drafts
from core.models.campaign import Campaign
from core.models.company import Company
from core.models.contact import Contact
from core.models.outreach_draft import OutreachDraft


@pytest.mark.unit
@pytest.mark.asyncio
async def test_campaign_manager_generation_and_exports(db_session: AsyncSession) -> None:
    # 1. Setup targeting database entities
    company = Company(
        name="Outur Tech",
        website="https://outur.ai",
        domain="outur.ai",
        industry="AI",
        score=95,
        tier="A",
        source="scout"
    )
    db_session.add(company)
    await db_session.commit()

    contact = Contact(
        company_id=company.id,
        full_name="Alice Recruiter",
        job_title="Talent Manager",
        email="alice@outur.ai",
        confidence_score=90
    )
    db_session.add(contact)
    await db_session.commit()

    # Create Campaign targetting contact
    campaign = Campaign(
        name="Launch Campaign",
        selected_companies=[str(company.id)],
        selected_contacts=[str(contact.id)],
        status="draft"
    )
    db_session.add(campaign)
    await db_session.commit()

    # 2. Run draft generation
    drafts = await generate_outreach_drafts(campaign_id=campaign.id, session=db_session)
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.campaign_id == campaign.id
    assert draft.contact_id == contact.id
    assert "Outur Tech" in draft.subject or "outur.ai" in draft.body or len(draft.subject) > 0
    assert len(draft.body) > 0

    # Refresh campaign status
    await db_session.refresh(campaign)
    assert campaign.status == "generated"

    # 3. Test export formats
    # CSV Export
    csv_data = await export_campaign_drafts(campaign.id, "csv", db_session)
    assert isinstance(csv_data, str)
    assert "Contact Name" in csv_data
    assert "Alice Recruiter" in csv_data
    assert "alice@outur.ai" in csv_data
    assert "Outur Tech" in csv_data

    # Gmail Export
    gmail_data = await export_campaign_drafts(campaign.id, "gmail_draft", db_session)
    assert isinstance(gmail_data, list)
    assert len(gmail_data) == 1
    raw_mime = gmail_data[0]["message"]["raw"]
    
    # Verify valid base64url decoding
    decoded_mime = base64.urlsafe_b64decode(raw_mime).decode("utf-8")
    assert "To: alice@outur.ai" in decoded_mime
    assert draft.subject in decoded_mime

    # Outlook Export
    outlook_data = await export_campaign_drafts(campaign.id, "outlook_draft", db_session)
    assert isinstance(outlook_data, list)
    assert len(outlook_data) == 1
    outlook_payload = outlook_data[0]
    assert outlook_payload["subject"] == draft.subject
    assert outlook_payload["body"]["content"] == draft.body
    assert outlook_payload["toRecipients"][0]["emailAddress"]["address"] == "alice@outur.ai"
