"""Unit tests for the Scorer Agent."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.scorer.agent import ScorerAgent
from core.models.company import Company
from core.models.contact import Contact


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scorer_agent_calculations(db_session: AsyncSession) -> None:
    """
    Test ScorerAgent calculates scores, tiers, and signals correctly
    based on company and contact properties.
    """
    # 1. Create a SaaS company (matches industry fit) with careers page
    company = Company(
        name="Test Stripe",
        website="https://stripe.com",
        domain="stripe.com",
        industry="SaaS & Payments",
        careers_page="https://stripe.com/careers",
        source="scout",
    )
    db_session.add(company)
    await db_session.commit()

    # 2. Add some mock contacts to simulate HR team size
    contact1 = Contact(
        company_id=company.id,
        full_name="Alice HR",
        job_title="HR Manager",
        email="alice@stripe.com",
        linkedin_url="https://linkedin.com/in/alice",
        confidence_score=100
    )
    db_session.add(contact1)
    await db_session.commit()

    agent = ScorerAgent()

    # 3. Run scorer
    result = await agent.run(
        company_id=str(company.id),
        session=db_session,
    )

    assert result["success"] is True
    score = result["data"]["score"]
    tier = result["data"]["tier"]
    signals = result["data"]["signals"]

    # Verify score fits boundaries and tier corresponds
    assert 0 <= score <= 100
    assert tier in ("A", "B", "C")
    assert "industry_fit" in signals
    assert "active_hiring" in signals
    assert "contact_info_available" in signals

    # Verify record was updated in database
    stmt = select(Company).where(Company.id == company.id)
    res = await db_session.execute(stmt)
    db_company = res.scalar_one()
    assert db_company.score == score
    assert db_company.tier == tier
    assert db_company.score_signals == signals
