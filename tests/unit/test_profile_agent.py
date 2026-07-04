"""Unit tests for the ResearchProfileAgent and caching logic."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.researcher.research_profile_agent import ResearchProfileAgent
from core.models.company import Company
from core.models.contact import Contact
from core.models.research_profile import ResearchProfile


@pytest.mark.unit
@pytest.mark.asyncio
async def test_research_profile_agent_flow_and_attribution(db_session: AsyncSession) -> None:
    """
    Test standard ResearchProfileAgent flow and confirm source URLs
    are correctly attached to insights.
    """
    company = Company(
        name="Stripe",
        website="https://stripe.com",
        domain="stripe.com",
        industry="SaaS",
        score=90,
        tier="A",
        source="scout",
    )
    db_session.add(company)
    await db_session.commit()

    agent = ResearchProfileAgent()
    result = await agent.run(company_id=str(company.id), session=db_session)
    
    assert result["success"] is True
    data = result["data"]
    
    # Confirm structured insights hold insight text and source URLs
    for list_key in ("hiring_signals", "growth_indicators", "public_pain_points"):
        assert len(data[list_key]) > 0
        for item in data[list_key]:
            assert "insight" in item
            assert "source_url" in item
            assert item["source_url"].startswith("http")

    # Confirm separate confidence scores are populated
    assert "llm_confidence" in data
    assert "data_quality" in data
    assert "freshness_score" in data
    assert "raw_evidence" in data
    assert "why_now" in data
    assert "recommended_pitch" in data
    assert "next_recommended_action" in data
    assert data["raw_evidence"] != {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_research_profile_cache_invalidation(db_session: AsyncSession) -> None:
    """
    Test automatic cache invalidation when company or contacts are updated.
    """
    # 1. Setup company
    company = Company(
        name="Plaid",
        website="https://plaid.com",
        domain="plaid.com",
        industry="Fintech",
        score=75,
        tier="B",
        source="scout",
    )
    db_session.add(company)
    await db_session.commit()

    agent = ResearchProfileAgent()

    # 2. Run agent to generate profile -> cached
    res1 = await agent.run(company_id=str(company.id), session=db_session)
    assert res1["success"] is True

    stmt = select(ResearchProfile).where(ResearchProfile.company_id == company.id)
    profile_db = (await db_session.execute(stmt)).scalar_one()
    
    # Save last_verified_at in a non-expired local variable
    initial_verified = profile_db.last_verified_at

    # Manually update summary in DB to check caching
    profile_db.summary = "Cached Profile"
    db_session.add(profile_db)
    await db_session.commit()

    # Check that running again (without refresh) returns cached profile
    res_cached = await agent.run(company_id=str(company.id), session=db_session)
    assert res_cached["data"]["summary"] == "Cached Profile"

    # 3. Simulate cache invalidation via company update
    # Set company updated_at to be in the future relative to the saved verified time
    company.updated_at = initial_verified + timedelta(seconds=10)
    db_session.add(company)
    await db_session.commit()

    # Verify next run auto-invalidates and updates summary
    res_invalidated = await agent.run(company_id=str(company.id), session=db_session)
    assert res_invalidated["data"]["summary"] != "Cached Profile"

    # 4. Simulate cache invalidation via contact update
    # Retrieve regenerated profile
    profile_db2 = (await db_session.execute(stmt)).scalar_one()
    
    # Save the updated last_verified_at BEFORE the commit expires it
    updated_verified = profile_db2.last_verified_at

    # Re-cache the profile summary
    profile_db2.summary = "Cached Profile 2"
    db_session.add(profile_db2)
    await db_session.commit()

    # Add a contact whose updated_at is newer than last_verified_at
    contact = Contact(
        company_id=company.id,
        full_name="Bob HR",
        job_title="Talent Manager",
        confidence_score=90
    )
    db_session.add(contact)
    await db_session.commit()

    # Manually shift contact's updated_at ahead of the saved verified time
    contact.updated_at = updated_verified + timedelta(seconds=10)
    db_session.add(contact)
    await db_session.commit()

    # Verify that contact update auto-invalidates the profile
    res_invalidated_contact = await agent.run(company_id=str(company.id), session=db_session)
    assert res_invalidated_contact["data"]["summary"] != "Cached Profile 2"
