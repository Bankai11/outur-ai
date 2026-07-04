"""
Scout Agent

Discovers target companies matching search queries or Ideal Customer Profile (ICP),
coordinates discovery providers, normalises results, validates data,
and deduplicates against the database.
"""

from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.scout.providers import PROVIDERS
from core.database import async_session_factory
from core.logger import get_logger
from core.models.company import Company

log = get_logger(__name__)


def extract_domain(website: str | None) -> str | None:
    """
    Extract and normalise the domain from a website URL.
    E.g. 'https://www.google.com/search' -> 'google.com'
    """
    if not website:
        return None
    try:
        url = website.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain if domain else None
    except Exception:
        return None


def validate_company(c_data: dict[str, Any]) -> bool:
    """
    Validates a company record. Must have a valid non-empty name.
    """
    name = c_data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return False
    return True


class ScoutAgent:
    """
    Coordinates discovery providers to search for companies, normalise results,
    deduplicate against the database, and save them.
    """

    agent_name: str = "scout"

    def __init__(self) -> None:
        log.debug("ScoutAgent initialised", agent=self.agent_name)

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Scout Agent.

        Parameters
        ----------
        industry: str | None
            Search query industry (e.g. 'SaaS').
        location: str | None
            Search query location (e.g. 'New York').
        company_size: str | None
            Search query headcount (e.g. '50-200').
        csv_content: str | None
            Raw CSV text to import.
        csv_file: str | None
            Path to CSV file to import.
        icp: dict | None
            Ideal Customer Profile filters (backward-compatible).
        limit: int
            Max companies to process (default 50).
        session: AsyncSession | None
            Optional database session.
        """
        log.info("Running Scout Agent", inputs=list(kwargs.keys()))

        # 1. Parse/extract inputs
        industry = kwargs.get("industry")
        location = kwargs.get("location")
        company_size = kwargs.get("company_size")
        csv_content = kwargs.get("csv_content")
        csv_file = kwargs.get("csv_file")
        limit = kwargs.get("limit", 50)

        # Backward compatibility with icp dict
        icp = kwargs.get("icp")
        if isinstance(icp, dict):
            if not industry and icp.get("industries"):
                # Use first industry
                industry = icp["industries"][0] if isinstance(icp["industries"], list) else icp["industries"]
            if not location and icp.get("geographies"):
                # Use first geography
                location = icp["geographies"][0] if isinstance(icp["geographies"], list) else icp["geographies"]
            if not company_size:
                min_hc = icp.get("headcount_min")
                max_hc = icp.get("headcount_max")
                if min_hc is not None or max_hc is not None:
                    company_size = f"{min_hc or 0}-{max_hc or 'unlimited'}"

        errors: list[str] = []
        raw_companies: list[dict[str, Any]] = []

        # 2. Coordinate discovery providers
        try:
            # Check if Manual CSV Import is triggered
            if csv_content or csv_file:
                csv_provider = next((p for p in PROVIDERS if p.name == "manual_csv"), None)
                if csv_provider:
                    results = await csv_provider.discover(
                        industry=industry,
                        location=location,
                        company_size=company_size,
                        csv_content=csv_content,
                        csv_file=csv_file,
                    )
                    raw_companies.extend(results)
                else:
                    errors.append("Manual CSV import provider is not registered.")
            else:
                from agents.scout.adapter import SearchAdapter
                search_providers = [p for p in PROVIDERS if p.name != "manual_csv"]
                adapter = SearchAdapter(search_providers)
                
                results = await adapter.search(
                    industry=industry, 
                    location=location, 
                    company_size=company_size
                )
                raw_companies.extend(results)

        except Exception as e:
            log.error("Failed to run discovery providers", error=str(e))
            return {
                "success": False,
                "data": {"companies": [], "total_found": 0, "new_count": 0},
                "errors": [str(e)],
            }
        # 3. Validate, normalise and deduplicate in memory
        validated: list[dict[str, Any]] = []
        seen_domains: set[str] = set()
        seen_linkedin: set[str] = set()
        seen_websites: set[str] = set()
        seen_names: set[str] = set()
        for raw in raw_companies:
            if validate_company(raw):
                name = raw["name"].strip()
                website = raw.get("website")
                linkedin_url = raw.get("linkedin_url")
                domain = extract_domain(website)

                if domain and domain in seen_domains:
                    continue
                if linkedin_url and linkedin_url in seen_linkedin:
                    continue
                if website and website in seen_websites:
                    continue
                if name.lower() in seen_names:
                    continue

                if domain:
                    seen_domains.add(domain)
                if linkedin_url:
                    seen_linkedin.add(linkedin_url)
                if website:
                    seen_websites.add(website)
                seen_names.add(name.lower())

                validated.append({
                    "name": name,
                    "website": website.strip() if website else None,
                    "domain": domain,
                    "linkedin_url": linkedin_url.strip() if linkedin_url else None,
                    "industry": raw.get("industry").strip() if raw.get("industry") else None,
                    "location": raw.get("location").strip() if raw.get("location") else None,
                    "careers_page": raw.get("careers_page").strip() if raw.get("careers_page") else None,
                    "source": raw.get("source", "unknown"),
                })

        # Apply limit if any
        validated = validated[:limit]

        # 4. Save to Database & Deduplicate
        session_param = kwargs.get("session")
        stats = {"new_count": 0, "updated_count": 0, "total_processed": 0}
        saved_companies: list[dict[str, Any]] = []

        try:
            if isinstance(session_param, AsyncSession):
                # Use standard provided session
                stats, saved_companies = await self._save_and_deduplicate(validated, session_param, commit=False)
            else:
                # Open a new transaction
                async with async_session_factory() as local_session:
                    try:
                        stats, saved_companies = await self._save_and_deduplicate(validated, local_session, commit=True)
                    except Exception:
                        await local_session.rollback()
                        raise

        except Exception as e:
            log.error("Failed to save and deduplicate companies in database", error=str(e))
            errors.append(f"Database error: {e}")
            return {
                "success": False,
                "data": {"companies": [], "total_found": len(validated), "new_count": 0},
                "errors": errors,
            }

        return {
            "success": len(errors) == 0 or len(saved_companies) > 0,
            "data": {
                "companies": saved_companies,
                "total_found": len(validated),
                "new_count": stats["new_count"],
                "updated_count": stats["updated_count"],
            },
            "errors": errors,
        }

    async def _save_and_deduplicate(
        self,
        companies: list[dict[str, Any]],
        session: AsyncSession,
        commit: bool = True,
    ) -> tuple[dict[str, int], list[dict[str, Any]]]:
        """
        Deduplicates companies using normalized domain, linkedin, website, and case-insensitive names,
        merging attributes for existing records and creating new ones.
        """
        new_count = 0
        updated_count = 0
        saved_list: list[dict[str, Any]] = []

        for item in companies:
            name = item["name"]
            domain = item["domain"]
            linkedin_url = item["linkedin_url"]
            website = item["website"]
            existing = None

            # Try to resolve by domain first
            if domain:
                stmt = select(Company).where(Company.domain == domain)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

            # Fallback: resolve by linkedin_url
            if not existing and linkedin_url:
                stmt = select(Company).where(Company.linkedin_url == linkedin_url)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

            # Fallback: resolve by website
            if not existing and website:
                stmt = select(Company).where(Company.website == website)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

            # Fallback: resolve by case-insensitive name match
            if not existing:
                stmt = select(Company).where(Company.name.ilike(name))
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

            if existing:
                # Merge missing/empty properties into existing company record
                modified = False
                if not existing.website and item["website"]:
                    existing.website = item["website"]
                    existing.domain = item["domain"]
                    modified = True
                if not existing.linkedin_url and item["linkedin_url"]:
                    existing.linkedin_url = item["linkedin_url"]
                    modified = True
                if not existing.industry and item["industry"]:
                    existing.industry = item["industry"]
                    modified = True
                if not existing.location and item["location"]:
                    existing.location = item["location"]
                    modified = True
                if not existing.careers_page and item["careers_page"]:
                    existing.careers_page = item["careers_page"]
                    modified = True

                if modified:
                    session.add(existing)
                    updated_count += 1
                
                saved_list.append({
                    "id": str(existing.id),
                    "name": existing.name,
                    "website": existing.website,
                    "domain": existing.domain,
                    "linkedin_url": existing.linkedin_url,
                    "industry": existing.industry,
                    "location": existing.location,
                    "careers_page": existing.careers_page,
                    "source": existing.source,
                })
            else:
                # Insert fresh record
                new_company = Company(
                    name=name,
                    website=item["website"],
                    domain=domain,
                    linkedin_url=item["linkedin_url"],
                    industry=item["industry"],
                    location=item["location"],
                    careers_page=item["careers_page"],
                    source=item["source"],
                )
                session.add(new_company)
                new_count += 1
                
                # We append a dict that will hold the populated UUID after flush
                saved_list.append({
                    "entity": new_company,
                    "name": name,
                    "website": item["website"],
                    "domain": domain,
                    "linkedin_url": item["linkedin_url"],
                    "industry": item["industry"],
                    "location": item["location"],
                    "careers_page": item["careers_page"],
                    "source": item["source"],
                })

        if commit:
            await session.commit()
        else:
            await session.flush()

        # Update IDs for newly created companies
        final_list: list[dict[str, Any]] = []
        for s in saved_list:
            if "entity" in s:
                entity = s.pop("entity")
                s["id"] = str(entity.id)
            final_list.append(s)

        stats = {
            "new_count": new_count,
            "updated_count": updated_count,
            "total_processed": len(companies),
        }
        return stats, final_list
