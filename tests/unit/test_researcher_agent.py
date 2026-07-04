"""Unit tests for the Researcher Agent."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.researcher.agent import ResearcherAgent
from core.models.company import Company
from core.models.contact import Contact


@pytest.mark.unit
@pytest.mark.asyncio
async def test_researcher_agent_full_flow(db_session: AsyncSession) -> None:
    """
    Test that ResearcherAgent resolves company, updates careers page,
    discovers contacts, validates/deduplicates them, and saves to DB.
    """
    # 1. Create a dummy company with missing careers page
    company = Company(
        name="Stripe",
        website="https://stripe.com",
        domain="stripe.com",
        source="scout",
    )
    db_session.add(company)
    await db_session.commit()

    agent = ResearcherAgent()

    # 2. Run agent with company ID
    result = await agent.run(
        company_id=str(company.id),
        session=db_session,
    )
    
    assert result["success"] is True
    contacts = result["data"]["contacts"]
    assert len(contacts) > 0

    # Verify careers_page was discovered and updated on company
    await db_session.refresh(company)
    assert company.careers_page == "https://stripe.com/careers"

    # Verify contacts exist in database linked to company
    stmt = select(Contact).where(Contact.company_id == company.id)
    res = await db_session.execute(stmt)
    db_contacts = res.scalars().all()
    assert len(db_contacts) == len(contacts)

    # 3. Check deduplication and merging
    # Let's manually clear email for one contact to verify it merges back
    first_c = db_contacts[0]
    saved_email = first_c.email
    first_c.email = None
    db_session.add(first_c)
    await db_session.commit()

    # Run agent again, should merge email back and not duplicate
    result2 = await agent.run(
        company_id=str(company.id),
        session=db_session,
    )
    assert result2["success"] is True

    # Refresh db contacts
    res2 = await db_session.execute(stmt)
    db_contacts2 = res2.scalars().all()
    assert len(db_contacts2) == len(db_contacts)

    # Verify email was restored
    restored_c = next((c for c in db_contacts2 if c.id == first_c.id), None)
    assert restored_c is not None
    assert restored_c.email == saved_email
