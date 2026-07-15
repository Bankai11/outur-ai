from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ConfidenceMetadata(BaseModel):
    score: float
    reason: str = Field(default="Heuristic evaluation")
    method: str = Field(default="heuristic")
    
    
class BuyingSignals(BaseModel):
    """Signals that indicate intent to buy or growth."""
    hiring_aggressively: bool | None = Field(default=None, description="Is the company hiring aggressively?")
    new_funding: bool | None = Field(default=None, description="Did they recently receive funding?")
    new_office: bool | None = Field(default=None, description="Did they open a new office?")
    product_launch: bool | None = Field(default=None, description="Did they recently launch a new product?")
    leadership_changes: bool | None = Field(default=None, description="Are there recent leadership changes?")
    recent_growth: bool | None = Field(default=None, description="Is the company experiencing recent growth?")
    job_openings: int | None = Field(default=None, description="Number of current job openings.")
    expansion: bool | None = Field(default=None, description="Is the company expanding?")


class TechnologySignals(BaseModel):
    """Technology stack signals."""
    crm: str | None = Field(default=None, description="CRM used.")
    hr_software: str | None = Field(default=None, description="HR software used.")
    ats: str | None = Field(default=None, description="Applicant Tracking System used.")
    analytics: list[str] | None = Field(default=None, description="Analytics tools used.")
    cloud_stack: list[str] | None = Field(default=None, description="Cloud infrastructure providers.")


class CompanyEnrichment(BaseModel):
    """Enriched data for a company."""
    industry: str | None = Field(default=None, description="Normalized Company industry.")
    raw_industry: str | None = Field(default=None, description="Raw industry from LLM.")
    industry_source: str = Field(default="gemini")
    
    employee_count_verification: int | None = Field(default=None, description="Verified employee count.")
    employee_count_source: str = Field(default="gemini")
    
    revenue_estimate: str | None = Field(default=None, description="Estimated revenue.")
    
    funding_stage: str | None = Field(default=None, description="Current funding stage (e.g. Series A).")
    funding_amount: str | None = Field(default=None, description="Total funding amount.")
    funding_source: str = Field(default="gemini")
    
    recent_funding: str | None = Field(default=None, description="Recent funding round details.")
    company_description: str | None = Field(default=None, description="Detailed company description.")
    
    technologies_used: list[str] | None = Field(default=None, description="Normalized general technologies used.")
    raw_technologies_used: list[str] | None = Field(default=None, description="Raw technologies from LLM.")
    technology_source: str = Field(default="gemini")
    hiring_trends: str | None = Field(default=None, description="Hiring trends or focus areas.")
    recent_news: list[str] | None = Field(default=None, description="Recent news snippets or URLs.")
    social_profiles: dict[str, str] | None = Field(default=None, description="Links to social profiles.")
    linkedin_source: str = Field(default="gemini")
    
    website_metadata: dict[str, str] | None = Field(default=None, description="Website metadata tags.")
    website_source: str = Field(default="gemini")
    
    headquarters: str | None = Field(default=None, description="Headquarters location.")
    company_size_confidence: str | None = Field(default=None, description="Confidence in company size (e.g. High/Medium/Low).")
    
    buying_signals: BuyingSignals | None = Field(default=None, description="Normalized signals of intent/growth.")
    raw_buying_signals: dict[str, Any] | None = Field(default=None, description="Raw buying signals.")
    
    technology_signals: TechnologySignals | None = Field(default=None, description="Technology stack signals.")
    
    confidence_scores: dict[str, ConfidenceMetadata] = Field(default_factory=dict, description="Rich confidence metadata for fields.")


class ContactEnrichment(BaseModel):
    """Enriched data for a contact."""
    work_email: str | None = Field(default=None, description="Verified work email address.")
    email_verification_status: str | None = Field(default=None, description="Status of email verification.")
    linkedin: str | None = Field(default=None, description="LinkedIn profile URL.")
    role_confidence: str | None = Field(default=None, description="Confidence in their role/title.")
    seniority: str | None = Field(default=None, description="Seniority level (e.g. C-Level, VP, Manager).")
    department: str | None = Field(default=None, description="Department they work in.")
    public_profile_links: list[str] | None = Field(default=None, description="Links to other public profiles.")
    linkedin_source: str = Field(default="gemini")
    confidence_scores: dict[str, ConfidenceMetadata] = Field(default_factory=dict, description="Rich confidence metadata for fields.")


class EnrichmentResult(BaseModel):
    """Overall enrichment result returned by an EnrichmentProvider."""
    company_enrichment: CompanyEnrichment | None = Field(default=None)
    contact_enrichment: dict[str, ContactEnrichment] = Field(
        default_factory=dict,
        description="Dictionary mapping contact IDs (UUID strings) to their enrichment data."
    )
    raw_data: dict[str, Any] | None = Field(default=None, description="Raw data from the provider for debugging/caching.")
    validation_status: str | None = Field(default=None, description="Status of validation (e.g. valid, partial, failed).")
    validation_errors: list[str] = Field(default_factory=list, description="List of validation/repair errors.")

