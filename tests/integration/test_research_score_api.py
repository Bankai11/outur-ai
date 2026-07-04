"""Integration tests for research and score endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.company import Company


@pytest.fixture(autouse=True)
def override_db_dependency(app: FastAPI, db_session: AsyncSession) -> None:
    from api.deps import get_session
    app.dependency_overrides[get_session] = lambda: db_session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_and_score_api_flow(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """
    Test the full research and score API flow:
    1. Create a dummy company.
    2. Call POST /api/v1/companies/{company_id}/research to discover contacts.
    3. Call POST /api/v1/companies/{company_id}/score to calculate score and tier.
    4. Call GET /api/v1/companies and verify payload contains contacts and score.
    """
    # 1. Create a dummy company in the DB
    company = Company(
        name="Stripe",
        website="https://stripe.com",
        domain="stripe.com",
        industry="FinTech",
        source="scout",
    )
    db_session.add(company)
    await db_session.commit()

    company_id_str = str(company.id)

    # 2. Call research API -> verify returns discovered contacts list
    response = await async_client.post(f"/api/v1/companies/{company_id_str}/research")
    assert response.status_code == 201
    research_data = response.json()
    assert research_data["success"] is True
    assert len(research_data["data"]["contacts"]) > 0
    
    first_contact = research_data["data"]["contacts"][0]
    assert "id" in first_contact
    assert "full_name" in first_contact
    assert "job_title" in first_contact
    assert "email" in first_contact

    # 3. Call score API -> verify returns calculated score details
    response = await async_client.post(f"/api/v1/companies/{company_id_str}/score")
    assert response.status_code == 200
    score_data = response.json()
    assert score_data["success"] is True
    assert score_data["data"]["company_id"] == company_id_str
    assert 0 <= score_data["data"]["score"] <= 100
    assert score_data["data"]["tier"] in ("A", "B", "C")
    assert len(score_data["data"]["signals"]) > 0

    # 4. Call GET /api/v1/companies -> verify returned company holds contacts and score
    response = await async_client.get("/api/v1/companies")
    assert response.status_code == 200
    list_data = response.json()
    assert list_data["total"] == 1
    
    returned_company = list_data["items"][0]
    assert returned_company["id"] == company_id_str
    assert returned_company["score"] == score_data["data"]["score"]
    assert returned_company["tier"] == score_data["data"]["tier"]
    assert len(returned_company["contacts"]) > 0
    assert returned_company["contacts"][0]["full_name"] == first_contact["full_name"]
