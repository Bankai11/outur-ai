from __future__ import annotations

import abc
from typing import Any

from agents.enrichment.models import EnrichmentResult, CompanyEnrichment, ContactEnrichment, BuyingSignals, TechnologySignals
from core.models.company import Company
from core.models.contact import Contact
from core.llm import get_llm_provider
from core.logger import get_logger

log = get_logger(__name__)


class EnrichmentProvider(abc.ABC):
    """
    Abstract base class for all enrichment providers.
    
    Providers are responsible for calling external APIs (e.g. Apollo, Hunter, LinkedIn)
    and returning standardized Pydantic models.
    """
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g. 'apollo', 'clearbit')."""
        pass

    @abc.abstractmethod
    async def enrich(
        self,
        company: Company,
        contacts: list[Contact]
    ) -> EnrichmentResult:
        """
        Enrich a company and its contacts.
        
        Must return an EnrichmentResult object. Failures should be logged,
        and partial data can be returned. Do not raise exceptions that would
        crash the campaign pipeline.
        """
        pass


class MockEnrichmentProvider(EnrichmentProvider):
    """
    A mock provider for development and testing. 
    It generates synthetic enrichment data based on the company and contacts.
    """
    
    @property
    def name(self) -> str:
        return "mock"

    async def enrich(
        self,
        company: Company,
        contacts: list[Contact]
    ) -> EnrichmentResult:
        import asyncio
        import random
        
        # Simulate network latency
        await asyncio.sleep(0.5)

        # Mock Company Enrichment
        industry = company.industry or "Software Development"
        revenue_estimates = ["$1M - $10M", "$10M - $50M", "$50M - $100M", "$100M+"]
        funding_stages = ["Seed", "Series A", "Series B", "Series C", "Public"]
        
        comp_enrichment = CompanyEnrichment(
            industry=industry,
            employee_count_verification=150,  # Deterministic size (sweet spot 50-250) for reliable test scores
            revenue_estimate=random.choice(revenue_estimates),
            funding_stage=random.choice(funding_stages),
            funding_amount=f"${random.randint(1, 100)}M",
            recent_funding="6 months ago",
            company_description=f"{company.name} is a leading provider in the {industry} space.",
            technologies_used=["AWS", "React", "Python", "PostgreSQL"],
            hiring_trends="Aggressively hiring engineering and sales.",
            recent_news=[f"{company.name} announces new product line.", f"{company.name} expands to Europe."],
            social_profiles={"twitter": f"https://twitter.com/{company.name.replace(' ', '')}"},
            headquarters="San Francisco, CA",
            company_size_confidence="High",
            buying_signals=BuyingSignals(
                hiring_aggressively=True,
                new_funding=random.choice([True, False]),
                new_office=False,
                product_launch=True,
                leadership_changes=False,
                recent_growth=True,
                job_openings=random.randint(5, 50),
                expansion=True
            ),
            technology_signals=TechnologySignals(
                crm="Salesforce",
                hr_software="Workday",
                ats="Greenhouse",
                analytics=["Google Analytics", "Mixpanel"],
                cloud_stack=["AWS", "Kubernetes"]
            )
        )

        # Mock Contact Enrichment
        contact_enrichment: dict[str, ContactEnrichment] = {}
        for contact in contacts:
            c_enrichment = ContactEnrichment(
                work_email=contact.email or f"{contact.full_name.split()[0].lower()}@{company.domain or 'example.com'}",
                email_verification_status="Verified",
                linkedin=contact.linkedin_url or f"https://linkedin.com/in/{contact.full_name.replace(' ', '').lower()}",
                role_confidence="High",
                seniority="Director" if "Director" in contact.job_title else "Manager",
                department="Engineering" if "Engineer" in contact.job_title else "Sales",
            )
            contact_enrichment[str(contact.id)] = c_enrichment

        return EnrichmentResult(
            company_enrichment=comp_enrichment,
            contact_enrichment=contact_enrichment,
            raw_data={"mock_field": "This is mock data"}
        )


class GeminiEnrichmentProvider(EnrichmentProvider):
    """
    Enrichment provider that uses Gemini with Google Search Grounding to find real-time 
    information about a company and its contacts.
    """
    
    @property
    def name(self) -> str:
        return "gemini"

    async def enrich(
        self,
        company: Company,
        contacts: list[Contact]
    ) -> EnrichmentResult:
        
        llm = get_llm_provider()
        
        contact_info = []
        for c in contacts:
            contact_info.append(f"Name: {c.full_name}, Title: {c.job_title}, ID: {c.id}")
            
        contacts_str = "\n".join(contact_info) if contact_info else "No contacts specified."
        
        prompt = f"""
You are an expert business researcher and data enrichment system.
I need you to thoroughly research the following company and its associated contacts.
Use Google Search Grounding to find real-time, accurate information.

Target Company:
Name: {company.name}
Domain: {company.domain or 'Unknown'}
Industry: {company.industry or 'Unknown'}
Location: {company.location or 'Unknown'}

Target Contacts (We need to enrich their profiles):
{contacts_str}

Please perform the following tasks:
1. Research the company's employee size, revenue estimates, funding stage and amount, recent news, technologies used, and hiring trends.
2. Identify specific buying signals such as aggressive hiring, new funding, new office, product launches, or recent growth.
3. Identify the technology stack (CRM, HR software, ATS, analytics, cloud).
4. For each contact provided above, find their likely work email, verified linkedin profile url, seniority, department, and role confidence. Use their exact ID from the list above as the key in the contact_enrichment dictionary.

Return the data STRICTLY matching the requested JSON schema. If you cannot find a specific piece of information, you may omit it or return null depending on the schema, but strive to be as complete as possible.
"""

        schema = EnrichmentResult.model_json_schema()
        
        log.info(f"Calling Gemini with Search Grounding to enrich company {company.name}")
        result_json = await llm.generate_json(
            prompt=prompt,
            schema=schema,
            use_search_grounding=True,
            timeout=45.0
        )
        
        if not result_json:
            log.warning(f"Failed to enrich company {company.name} using Gemini (no output)")
            return EnrichmentResult(validation_status="failed", validation_errors=["No output from LLM"])
            
        from agents.enrichment.validation import ValidationPipeline
        return await ValidationPipeline.process(result_json)
