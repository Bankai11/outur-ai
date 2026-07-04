"""Integration tests for Campaign API endpoints."""

from __future__ import annotations

import base64
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.campaign import Campaign
from core.models.company import Company
from core.models.contact import Contact


@pytest.fixture(autouse=True)
def override_db_dependency(app: FastAPI, db_session: AsyncSession) -> None:
    from api.deps import get_session
    app.dependency_overrides[get_session] = lambda: db_session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_campaign_api_flow(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """
    Test the full campaign api flow:
    1. Create company and contact.
    2. POST /api/v1/campaigns to create campaign.
    3. GET /api/v1/campaigns to verify it lists campaign.
    4. POST /api/v1/campaigns/{id}/generate to draft emails.
    5. POST /api/v1/campaigns/{id}/export formats.
    """
    # 1. Setup DB objects
    company = Company(
        name="Outur Tech",
        website="https://outur.ai",
        domain="outur.ai",
        industry="AI",
        score=90,
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

    # 2. Create campaign via API
    payload = {
        "name": "Outreach Campaign",
        "selected_companies": [str(company.id)],
        "selected_contacts": [str(contact.id)],
    }
    response = await async_client.post("/api/v1/campaigns", json=payload)
    assert response.status_code == 201
    campaign_data = response.json()
    assert campaign_data["name"] == "Outreach Campaign"
    assert campaign_data["status"] == "draft"
    campaign_id = campaign_data["id"]

    # 3. GET Campaigns list
    list_response = await async_client.get("/api/v1/campaigns")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == campaign_id

    # 4. Generate outreach drafts
    gen_response = await async_client.post(f"/api/v1/campaigns/{campaign_id}/generate")
    assert gen_response.status_code == 200
    gen_data = gen_response.json()
    assert gen_data["success"] is True
    assert len(gen_data["data"]) == 1
    assert "subject" in gen_data["data"][0]
    assert "body" in gen_data["data"][0]

    # 5. Export to CSV
    csv_response = await async_client.post(f"/api/v1/campaigns/{campaign_id}/export?format=csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "attachment" in csv_response.headers["content-disposition"]
    csv_text = csv_response.text
    assert "Alice Recruiter" in csv_text
    assert "alice@outur.ai" in csv_text

    # Export to Gmail
    gmail_response = await async_client.post(f"/api/v1/campaigns/{campaign_id}/export?format=gmail_draft")
    assert gmail_response.status_code == 200
    gmail_data = gmail_response.json()
    assert gmail_data["success"] is True
    assert len(gmail_data["data"]) == 1
    assert "raw" in gmail_data["data"][0]["message"]
    
    # Export to Outlook
    outlook_response = await async_client.post(f"/api/v1/campaigns/{campaign_id}/export?format=outlook_draft")
    assert outlook_response.status_code == 200
    outlook_data = outlook_response.json()
    assert outlook_data["success"] is True
    assert len(outlook_data["data"]) == 1
    assert outlook_data["data"][0]["toRecipients"][0]["emailAddress"]["address"] == "alice@outur.ai"
