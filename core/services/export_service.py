"""
Export Service

Writes campaign pipeline results (companies, contacts, research profiles,
and outreach drafts) to CSV and JSON files on disk.
"""

from __future__ import annotations

import csv
import json
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.models.outreach_draft import OutreachDraft
from core.models.research_profile import ResearchProfile

log = get_logger(__name__)


class ExportService:
    """Handles exporting campaign pipeline results to CSV and JSON files."""

    async def export_all(
        self,
        company_ids: list[str],
        output_dir: str,
        session: AsyncSession,
    ) -> None:
        """Run every export step and write files to *output_dir*.

        Args:
            company_ids: UUID strings of discovered companies.
            output_dir: Destination directory (must already exist).
            session: Active database session.
        """
        co_uuids = [_to_uuid(cid) for cid in company_ids]

        companies = await self._fetch_companies(co_uuids, session)
        contacts = await self._fetch_contacts(co_uuids, session)
        profiles = await self._fetch_profiles(co_uuids, session)
        drafts = await self._fetch_drafts(session)

        self._write_companies_csv(companies, output_dir)
        self._write_contacts_csv(contacts, output_dir)
        self._write_tier_a_csv(companies, output_dir)
        self._write_research_profiles_json(profiles, output_dir)
        self._write_outreach_drafts(drafts, contacts, output_dir)

    # ------------------------------------------------------------------
    # Database fetchers
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_companies(
        co_uuids: list[uuid.UUID], session: AsyncSession
    ) -> list[Company]:
        """Return Company ORM objects matching *co_uuids*."""
        stmt = select(Company).where(Company.id.in_(co_uuids))
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def _fetch_contacts(
        co_uuids: list[uuid.UUID], session: AsyncSession
    ) -> list[Contact]:
        """Return Contact ORM objects for the given company UUIDs."""
        stmt = select(Contact).where(Contact.company_id.in_(co_uuids))
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def _fetch_profiles(
        co_uuids: list[uuid.UUID], session: AsyncSession
    ) -> list[ResearchProfile]:
        """Return ResearchProfile ORM objects for the given company UUIDs."""
        stmt = select(ResearchProfile).where(ResearchProfile.company_id.in_(co_uuids))
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def _fetch_drafts(session: AsyncSession) -> list[OutreachDraft]:
        """Return every OutreachDraft in the database."""
        stmt = select(OutreachDraft)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    # ------------------------------------------------------------------
    # CSV / JSON writers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_companies_csv(companies: list[Company], output_dir: str) -> None:
        """Write *companies.csv* with discovered company data."""
        path = os.path.join(output_dir, "companies.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            headers = ["ID", "Name", "Website", "Domain", "Industry", "Location",
                        "Source", "Score", "Tier"]
            writer.writerow(headers)
            for co in companies:
                writer.writerow([
                    co.id, co.name, co.website, co.domain,
                    co.industry, co.location, co.source, co.score, co.tier,
                ])

    @staticmethod
    def _write_contacts_csv(contacts: list[Contact], output_dir: str) -> None:
        """Write *contacts.csv* with discovered contact data."""
        path = os.path.join(output_dir, "contacts.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            headers = ["ID", "Company ID", "Full Name", "Job Title", "Email",
                        "LinkedIn URL", "Confidence Score"]
            writer.writerow(headers)
            for c in contacts:
                writer.writerow([
                    c.id, c.company_id, c.full_name, c.job_title,
                    c.email, c.linkedin_url, c.confidence_score,
                ])

    @staticmethod
    def _write_tier_a_csv(companies: list[Company], output_dir: str) -> None:
        """Write *tier_a.csv* with Tier-A companies only."""
        tier_a = [co for co in companies if co.tier == "A"]
        path = os.path.join(output_dir, "tier_a.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Website", "Domain", "Industry", "Score"])
            for co in tier_a:
                writer.writerow([co.id, co.name, co.website, co.domain, co.industry, co.score])

    @staticmethod
    def _write_research_profiles_json(
        profiles: list[ResearchProfile], output_dir: str
    ) -> None:
        """Write *research_profiles.json* summarising research data."""
        data = []
        for p in profiles:
            data.append({
                "company_id": str(p.company_id),
                "summary": p.summary,
                "hiring_signals": p.hiring_signals,
                "growth_indicators": p.growth_indicators,
                "public_pain_points": p.public_pain_points,
                "why_now": p.why_now,
                "recommended_pitch": p.recommended_pitch,
                "best_contact": p.best_contact,
                "outreach_angles": p.outreach_angles,
                "next_recommended_action": p.next_recommended_action,
                "llm_confidence": p.llm_confidence,
                "data_quality": p.data_quality,
                "freshness_score": p.freshness_score,
            })
        path = os.path.join(output_dir, "research_profiles.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _write_outreach_drafts(
        drafts: list[OutreachDraft],
        contacts: list[Contact],
        output_dir: str,
    ) -> None:
        """Write individual ``draft_*.txt`` files for each outreach draft."""
        contacts_map = {c.id: c for c in contacts}
        for d in drafts:
            c = contacts_map.get(d.contact_id)
            c_name = c.full_name.replace(" ", "_") if c else str(d.contact_id)
            draft_filepath = os.path.join(output_dir, "outreach_drafts", f"draft_{c_name}.txt")
            with open(draft_filepath, "w", encoding="utf-8") as f:
                f.write(f"Subject: {d.subject}\n")
                f.write(f"To: {c.email if c else ''}\n")
                f.write("=" * 60 + "\n")
                f.write(d.body)


def _to_uuid(value: str) -> uuid.UUID:
    """Convert a string to a UUID object."""
    return uuid.UUID(value)
