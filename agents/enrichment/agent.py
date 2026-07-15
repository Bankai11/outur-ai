"""
Enrichment Agent

Integrates into the campaign pipeline to enrich companies and contacts with 
additional data (industry, size, funding, buying signals, tech stack).
"""
from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.enrichment.cache import InMemoryEnrichmentCache
from agents.enrichment.providers import GeminiEnrichmentProvider
from agents.enrichment.service import EnrichmentService
from core.database import async_session_factory
from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.utils.exceptions import NotFoundError

log = get_logger(__name__)


class EnrichmentAgent:
    """Enriches companies and contacts using the EnrichmentService."""
    
    agent_name: str = "enrichment"
    
    def __init__(self) -> None:
        log.debug("EnrichmentAgent initialised", agent=self.agent_name)
        from core.config import get_settings
        settings = get_settings()
        
        # In a real app with DI, these would be injected.
        cache = InMemoryEnrichmentCache()
        
        if settings.app_env == "testing":
            from agents.enrichment.providers import MockEnrichmentProvider
            providers = [MockEnrichmentProvider()]
        else:
            providers = [GeminiEnrichmentProvider()]
            
        self.service = EnrichmentService(providers=providers, cache=cache)

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Enrichment Agent.

        Parameters
        ----------
        company_id: str | uuid.UUID
            The ID of the company to enrich.
        session: AsyncSession | None
            Optional database session.
        """
        log.info("Running Enrichment Agent", inputs=list(kwargs.keys()))

        company_id = kwargs.get("company_id")
        if not company_id:
            return {"success": False, "errors": ["Missing company_id"]}

        session_param = kwargs.get("session")
        try:
            if isinstance(session_param, AsyncSession):
                result = await self._execute_agent(company_id=company_id, session=session_param, commit=False)
            else:
                async with async_session_factory() as local_session:
                    try:
                        result = await self._execute_agent(company_id=company_id, session=local_session, commit=True)
                    except Exception:
                        await local_session.rollback()
                        raise
            return result
        except NotFoundError as e:
            log.error("Company not found during enrichment", error=e.detail)
            return {"success": False, "data": {}, "errors": [e.detail]}
        except Exception as e:
            log.error("Failed to run Enrichment Agent", error=str(e))
            return {"success": False, "data": {}, "errors": [str(e)]}

    async def _execute_agent(
        self,
        company_id: Any,
        session: AsyncSession,
        company: Any = None,
        commit: bool = True
    ) -> dict[str, Any]:
        
        # 1. Load Company
        from core.services.company_resolver import resolve_company
        company_obj = await resolve_company(company_id, session, company=company)

        # 2. Load Contacts
        contact_stmt = select(Contact).where(Contact.company_id == company_obj.id)
        contact_res = await session.execute(contact_stmt)
        contacts = list(contact_res.scalars().all())

        # 3. Enrich via Service
        enrichment_result = await self.service.enrich(company_obj, contacts)

        # 4. Save Enrichment Data
        modified = False
        
        if enrichment_result.company_enrichment:
            company_obj.enrichment_data = enrichment_result.company_enrichment.model_dump()
            session.add(company_obj)
            modified = True
            
        if enrichment_result.contact_enrichment:
            for contact in contacts:
                c_data = enrichment_result.contact_enrichment.get(str(contact.id))
                if c_data:
                    contact.enrichment_data = c_data.model_dump()
                    session.add(contact)
                    modified = True

        if modified:
            if commit:
                await session.commit()
            else:
                await session.flush()

        log.info("Enrichment complete", company_id=str(company_obj.id), modified=modified)

        return {
            "success": True,
            "data": {
                "company_id": str(company_obj.id),
                "enrichment": enrichment_result.model_dump()
            },
            "errors": []
        }
