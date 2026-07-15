"""Unit tests for the Scout Agent."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.scout.agent import ScoutAgent, extract_domain
from core.models.company import Company


@pytest.mark.unit
def test_extract_domain() -> None:
    """Test normalized domain extraction from various URL formats."""
    assert extract_domain("https://www.google.com/search?q=test") == "google.com"
    assert extract_domain("http://stripe.com/") == "stripe.com"
    assert extract_domain("plaid.com") == "plaid.com"
    assert extract_domain("https://subdomain.domain.co.uk") == "subdomain.domain.co.uk"
    assert extract_domain("") is None
    assert extract_domain(None) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scout_agent_run_and_deduplicate(db_session: AsyncSession) -> None:
    """
    Test ScoutAgent coordinates search, validates, and saves records.
    Verifies that running twice with duplicate entries merges properties.
    """
    agent = ScoutAgent()

    # Step 1: Run scout with criteria
    result = await agent.run(
        industry="FinTech",
        location="San Francisco",
        session=db_session,
    )
    
    assert result["success"] is True
    companies = result["data"]["companies"]
    assert len(companies) > 0
    new_count = result["data"]["new_count"]
    assert new_count > 0

    # Ensure records exist in database
    stmt = select(Company)
    res = await db_session.execute(stmt)
    db_companies = res.scalars().all()
    assert len(db_companies) == len(companies)

    # Find Stripe or Plaid in db
    stripe = next((c for c in db_companies if c.name.lower() == "stripe"), None)
    if stripe:
        assert stripe.domain == "stripe.com"
        assert stripe.industry.lower() == "fintech"
        # We manually clear some field to verify merge logic in Step 2
        stripe.linkedin_url = None
        db_session.add(stripe)
        await db_session.commit()

    # Step 2: Run again with same criteria
    # This should merge the cleared linkedin_url of Stripe but not duplicate it
    result2 = await agent.run(
        industry="FinTech",
        location="San Francisco",
        session=db_session,
    )
    
    assert result2["success"] is True
    assert result2["data"]["new_count"] == 0
    assert result2["data"]["updated_count"] >= (1 if stripe else 0)

    # Check database count hasn't changed
    res2 = await db_session.execute(stmt)
    db_companies2 = res2.scalars().all()
    assert len(db_companies2) == len(db_companies)

    # Check Stripe LinkedIn url is restored
    if stripe:
        stripe_updated = next((c for c in db_companies2 if c.name.lower() == "stripe"), None)
        assert stripe_updated is not None
        assert stripe_updated.linkedin_url is not None
