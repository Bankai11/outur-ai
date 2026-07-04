"""Integration tests for company profiling API endpoint."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
async def test_company_profiling_api_flow(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """
    Test the full profiling API flow:
    1. Create a dummy company with associated contacts.
    2. Call POST /api/v1/companies/{company_id}/profile to generate a research profile.
    3. Call GET /api/v1/companies and verify payload contains the research_profile.
    """
    # 1. Create company and contacts in database
    company = Company(
        name="Stripe",
        website="https://stripe.com",
        domain="stripe.com",
        industry="Payments",
        source="scout",
    )
    db_session.add(company)
    await db_session.commit()

    contact = Contact(
        company_id=company.id,
        full_name="Jane HR",
        job_title="HR Director",
        confidence_score=90
    )
    db_session.add(contact)
    await db_session.commit()

    company_id_str = str(company.id)

    # 2. Call profile API -> verify it generates research profile
    response = await async_client.post(f"/api/v1/companies/{company_id_str}/profile")
    assert response.status_code == 201
    profile_data = response.json()
    assert profile_data["success"] is True
    assert profile_data["data"]["company_id"] == company_id_str
    assert "summary" in profile_data["data"]
    assert profile_data["data"]["best_contact"] is not None
    assert profile_data["data"]["best_contact"]["full_name"] == "Jane HR"

    # 3. Call GET /api/v1/companies -> verify company in response contains research_profile
    response = await async_client.get("/api/v1/companies")
    assert response.status_code == 200
    list_data = response.json()
    assert list_data["total"] == 1
    
    returned_company = list_data["items"][0]
    assert returned_company["id"] == company_id_str
    assert returned_company["research_profile"] is not None
    assert returned_company["research_profile"]["summary"] == profile_data["data"]["summary"]
