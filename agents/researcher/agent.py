"""
Researcher Agent

Discovers relevant HR/hiring decision-makers for a given company.
Runs contact providers in parallel, normalises, validates,
deduplicates, and saves contacts linked to the Company database table.
"""

from __future__ import annotations

import asyncio
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.researcher.providers import PROVIDERS
from core.database import async_session_factory
from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.utils.exceptions import NotFoundError

log = get_logger(__name__)


def validate_contact(c_data: dict[str, Any]) -> bool:
    """
    Validates a discovered contact profile.
    """
    if not c_data.get("full_name") or not isinstance(c_data["full_name"], str) or not c_data["full_name"].strip():
        return False
    if not c_data.get("job_title") or not isinstance(c_data["job_title"], str) or not c_data["job_title"].strip():
        return False
    return True


class ResearcherAgent:
    """
    Agent responsible for finding decision-makers within target companies.
    """

    agent_name: str = "researcher"

    def __init__(self) -> None:
        log.debug("ResearcherAgent initialised", agent=self.agent_name)

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Researcher Agent.

        Parameters
        ----------
        company_id: str | uuid.UUID | None
            The ID of the company to research.
        company: Company | None
            An already loaded Company object.
        persona: str | None
            Optional target persona query (e.g. 'HR Manager').
        session: AsyncSession | None
            Optional database session.
        """
        log.info("Running Researcher Agent", inputs=list(kwargs.keys()))

        company_id = kwargs.get("company_id")
        company = kwargs.get("company")
        session_param = kwargs.get("session")

        errors: list[str] = []
        raw_contacts: list[dict[str, Any]] = []

        try:
            if isinstance(session_param, AsyncSession):
                # Use standard provided session
                result = await self._execute_agent(
                    company_id=company_id,
                    company=company,
                    session=session_param,
                    commit=False
                )
            else:
                # Open a new transaction
                async with async_session_factory() as local_session:
                    try:
                        result = await self._execute_agent(
                            company_id=company_id,
                            company=company,
                            session=local_session,
                            commit=True
                        )
                    except Exception:
                        await local_session.rollback()
                        raise
            return result
        except NotFoundError as e:
            log.error("Company not found during research", error=e.detail)
            return {
                "success": False,
                "data": {"contacts": []},
                "errors": [e.detail]
            }
        except Exception as e:
            log.error("Failed to run Researcher Agent", error=str(e))
            return {
                "success": False,
                "data": {"contacts": []},
                "errors": [str(e)]
            }

    async def _execute_agent(
        self,
        company_id: Any,
        company: Any,
        session: AsyncSession,
        commit: bool = True
    ) -> dict[str, Any]:
        # 1. Resolve Company record
        company_obj: Company | None = None
        if company and isinstance(company, Company):
            company_obj = company
        elif company_id:
            # Parse UUID safely
            if isinstance(company_id, str):
                try:
                    resolved_uuid = uuid.UUID(company_id)
                except ValueError:
                    raise NotFoundError("Company", company_id)
            else:
                resolved_uuid = company_id

            stmt = select(Company).where(Company.id == resolved_uuid)
            res = await session.execute(stmt)
            company_obj = res.scalar_one_or_none()

        if not company_obj:
            raise NotFoundError("Company", company_id)

        log.info("Researched company identified", company_name=company_obj.name)

        # 2. Discover/Update careers page if missing
        if not company_obj.careers_page:
            domain = company_obj.domain
            if domain:
                company_obj.careers_page = f"https://{domain}/careers"
                session.add(company_obj)
                log.info(
                    "Discovered careers page URL",
                    company=company_obj.name,
                    careers_page=company_obj.careers_page
                )
        # 3. Query all providers in parallel
        raw_contacts: list[dict[str, Any]] = []
        tasks = [
            p.discover_contacts(company_obj.name, company_obj.domain)
            for p in PROVIDERS
        ]
        
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)
        errors: list[str] = []

        for provider, result in zip(PROVIDERS, provider_results):
            if isinstance(result, Exception):
                err_msg = f"Provider {provider.name} failed: {result}"
                log.error(err_msg, exc_info=result)
                errors.append(err_msg)
            else:
                raw_contacts.extend(result)

        # 4. Normalize and validate
        validated: list[dict[str, Any]] = []
        for raw in raw_contacts:
            if validate_contact(raw):
                validated.append({
                    "full_name": raw["full_name"].strip(),
                    "job_title": raw["job_title"].strip(),
                    "linkedin_url": raw.get("linkedin_url").strip() if raw.get("linkedin_url") else None,
                    "email": raw.get("email").strip().lower() if raw.get("email") else None,
                    "source_url": raw.get("source_url").strip() if raw.get("source_url") else None,
                    "confidence_score": int(raw.get("confidence_score", 100)),
                })

        # 5. Deduplicate and save
        saved_contacts = await self._save_contacts(company_obj.id, validated, session, commit=commit)

        return {
            "success": len(errors) == 0 or len(saved_contacts) > 0,
            "data": {
                "contacts": saved_contacts
            },
            "errors": errors
        }

    async def _save_contacts(
        self,
        company_id: uuid.UUID,
        contacts_data: list[dict[str, Any]],
        session: AsyncSession,
        commit: bool = True
    ) -> list[dict[str, Any]]:
        """
        Deduplicates contacts internally and against DB records for this company.
        """
        # Fetch existing contacts in DB for this company
        stmt = select(Contact).where(Contact.company_id == company_id)
        res = await session.execute(stmt)
        db_contacts = list(res.scalars().all())

        # In-memory deduplication tracking
        seen_emails: set[str] = set()
        seen_linkedin: set[str] = set()
        seen_names_roles: set[tuple[str, str]] = set()

        # Seed sets with existing DB contacts
        for db_c in db_contacts:
            if db_c.email:
                seen_emails.add(db_c.email.lower())
            if db_c.linkedin_url:
                seen_linkedin.add(db_c.linkedin_url.lower())
            seen_names_roles.add((db_c.full_name.lower(), db_c.job_title.lower()))

        saved_list: list[dict[str, Any]] = []

        for item in contacts_data:
            email = item["email"]
            linkedin = item["linkedin_url"]
            name = item["full_name"]
            title = item["job_title"]

            # Deduplicate check inside current batch
            if email and email.lower() in seen_emails:
                # Resolve match from existing db_contacts
                matching_db = next((c for c in db_contacts if c.email and c.email.lower() == email.lower()), None)
                if matching_db:
                    await self._merge_contact(matching_db, item, session)
                continue
            if linkedin and linkedin.lower() in seen_linkedin:
                matching_db = next((c for c in db_contacts if c.linkedin_url and c.linkedin_url.lower() == linkedin.lower()), None)
                if matching_db:
                    await self._merge_contact(matching_db, item, session)
                continue
            if (name.lower(), title.lower()) in seen_names_roles:
                matching_db = next((c for c in db_contacts if c.full_name.lower() == name.lower() and c.job_title.lower() == title.lower()), None)
                if matching_db:
                    await self._merge_contact(matching_db, item, session)
                continue

            # Update unique sets
            if email:
                seen_emails.add(email.lower())
            if linkedin:
                seen_linkedin.add(linkedin.lower())
            seen_names_roles.add((name.lower(), title.lower()))

            # Create new contact
            new_contact = Contact(
                company_id=company_id,
                full_name=name,
                job_title=title,
                linkedin_url=linkedin,
                email=email,
                source_url=item["source_url"],
                confidence_score=item["confidence_score"]
            )
            session.add(new_contact)
            
            # Map entity to update its UUID on flush
            saved_list.append({
                "entity": new_contact,
                "full_name": name,
                "job_title": title,
                "linkedin_url": linkedin,
                "email": email,
                "source_url": item["source_url"],
                "confidence_score": item["confidence_score"]
            })

        # Append unmodified/merged existing contacts to returned payload
        for db_c in db_contacts:
            saved_list.append({
                "id": str(db_c.id),
                "full_name": db_c.full_name,
                "job_title": db_c.job_title,
                "linkedin_url": db_c.linkedin_url,
                "email": db_c.email,
                "source_url": db_c.source_url,
                "confidence_score": db_c.confidence_score
            })

        if commit:
            await session.commit()
        else:
            await session.flush()

        # Final serialization mapping ID
        final_list = []
        for s in saved_list:
            if "entity" in s:
                entity = s.pop("entity")
                s["id"] = str(entity.id)
            final_list.append(s)

        return final_list

    async def _merge_contact(self, existing: Contact, new_item: dict[str, Any], session: AsyncSession) -> None:
        """Merge discovered fields into existing record."""
        modified = False
        if not existing.linkedin_url and new_item["linkedin_url"]:
            existing.linkedin_url = new_item["linkedin_url"]
            modified = True
        if not existing.email and new_item["email"]:
            existing.email = new_item["email"]
            modified = True
        if not existing.source_url and new_item["source_url"]:
            existing.source_url = new_item["source_url"]
            modified = True
        if modified:
            session.add(existing)
