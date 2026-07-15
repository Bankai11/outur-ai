from typing import List, Optional
from pydantic import BaseModel, Field

class CampaignRequirements(BaseModel):
    industry: Optional[str] = None
    employee_range: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    growth_stage: Optional[str] = None
    funding_stage: Optional[str] = None
    technologies_used: List[str] = Field(default_factory=list)
    hiring_activity: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    exclude_industries: List[str] = Field(default_factory=list)
    exclude_company_sizes: List[str] = Field(default_factory=list)
    exclude_existing_customers: bool = False
    
    # Discovery configuration
    min_confidence: float = 0.5
    min_icp_score: int = 50

class RankedCompany(BaseModel):
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    country: Optional[str] = None
    lead_score: int = Field(ge=0, le=100)
    icp_match_score: int = Field(ge=0, le=100)
    buying_signals: List[str] = Field(default_factory=list)
    growth_signals: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reason_for_selection: str

class RankedProspectList(BaseModel):
    companies: List[RankedCompany]
