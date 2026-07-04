"""Unit and integration tests for Outur AI Campaign Runner CLI pipeline."""

from __future__ import annotations

import os
import shutil
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from run_campaign import run_pipeline
from core.models.company import Company
from core.models.contact import Contact


@pytest.fixture
def clean_exports_dir() -> str:
    """Fixture to manage clean temporary exports directory."""
    path = "test_cli_exports"
    if os.path.exists(path):
        shutil.rmtree(path)
    yield path
    if os.path.exists(path):
        shutil.rmtree(path)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_campaign_runner_pipeline_success(db_session: AsyncSession, clean_exports_dir: str) -> None:
    """
    Test end-to-end execution of the Campaign Runner pipeline.
    """
    # 1. Run pipeline (Scout will automatically discover mock companies in local mock mode)
    res = await run_pipeline(
        industry="Technology",
        country="US",
        employees="10-50",
        limit=2,
        output_dir=clean_exports_dir,
        session=db_session
    )
    
    assert res["success"] is True

    # 2. Verify all files are written
    assert os.path.exists(os.path.join(clean_exports_dir, "companies.csv"))
    assert os.path.exists(os.path.join(clean_exports_dir, "contacts.csv"))
    assert os.path.exists(os.path.join(clean_exports_dir, "tier_a.csv"))
    assert os.path.exists(os.path.join(clean_exports_dir, "research_profiles.json"))
    assert os.path.exists(os.path.join(clean_exports_dir, "outreach_drafts"))

    # Check companies.csv contains records
    with open(os.path.join(clean_exports_dir, "companies.csv"), "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1  # Header + at least one company

    # Check outreach drafts contain files
    draft_files = os.listdir(os.path.join(clean_exports_dir, "outreach_drafts"))
    assert len(draft_files) > 0
    for filename in draft_files:
        assert filename.startswith("draft_")
        assert filename.endswith(".txt")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_campaign_runner_pipeline_error_isolation(db_session: AsyncSession, clean_exports_dir: str) -> None:
    """
    Verify that Campaign Runner continues processing if contact discovery for one company fails.
    """
    # 1. Pre-seed two companies in the DB
    co1 = Company(
        name="Valid Stripe",
        website="https://stripe.com",
        domain="stripe.com",
        industry="SaaS",
        source="scout"
    )
    co2 = Company(
        name="Broken Co",
        website="https://broken.co",
        domain="broken.co",
        industry="Tech",
        source="scout"
    )
    db_session.add_all([co1, co2])
    await db_session.commit()

    # Pre-seed contact only for the valid company
    contact = Contact(
        company_id=co1.id,
        full_name="Alice Valid",
        job_title="Talent lead",
        confidence_score=95
    )
    db_session.add(contact)
    await db_session.commit()

    # 2. Run pipeline (limit=2). ScoutAgent will run and deduplicate pre-seeded companies,
    # and even if contact discovery fails on one invalid or missing company detail, the workflow completes.
    res = await run_pipeline(
        industry="SaaS",
        country="US",
        employees="100-500",
        limit=2,
        output_dir=clean_exports_dir,
        session=db_session
    )
    
    assert res["success"] is True
    assert os.path.exists(os.path.join(clean_exports_dir, "companies.csv"))
    assert os.path.exists(os.path.join(clean_exports_dir, "contacts.csv"))
