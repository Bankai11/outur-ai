import os
import yaml
from pathlib import Path
from pydantic import BaseModel, Field

class TriggerDefinition(BaseModel):
    event: str = Field(description="The event or signal (e.g., 'Hiring surge').")
    description: str = Field(description="Details on what this trigger looks like.")
    relevance_to_product: str = Field(description="Why this trigger indicates they need the product.")

class PlaybookDefinition(BaseModel):
    name: str = Field(description="The name of the playbook (e.g., 'Growth Playbook').")
    target_triggers: list[str] = Field(default_factory=list, description="Which triggers this playbook applies to.")
    messaging_strategy: str = Field(description="How to position the product for this playbook.")
    objection_handling: dict[str, str] = Field(default_factory=dict)
    cta_style: str = Field(description="What kind of call to action to use.")

class BusinessProfile(BaseModel):
    company_name: str = Field(description="Name of the company running the outreach.")
    product_name: str = Field(description="Name of the specific product being sold.")
    elevator_pitch: str = Field(description="One-sentence description of the product.")
    target_icp: str = Field(description="Description of the Ideal Customer Profile.")
    primary_buyer_personas: list[str] = Field(default_factory=list)
    core_pain_points_solved: list[str] = Field(default_factory=list)
    key_differentiators: list[str] = Field(default_factory=list)
    customer_outcomes: list[str] = Field(default_factory=list)
    desired_outcomes: list[str] = Field(default_factory=list)
    objection_handling: dict[str, str] = Field(default_factory=dict)
    call_to_action_styles: list[str] = Field(default_factory=list)
    subject_line_rules: list[str] = Field(default_factory=list)
    brand_voice: str = Field(default="Professional and confident")
    email_tone: str = Field(default="Consultative")
    follow_up_strategy: list[str] = Field(default_factory=list)
    case_studies: list[str] = Field(default_factory=list)
    social_proof: list[str] = Field(default_factory=list)
    pricing_positioning: str = Field(default="")
    competitor_positioning: dict[str, str] = Field(default_factory=dict)
    messaging_guardrails: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    
    triggers: list[TriggerDefinition] = Field(default_factory=list)
    playbooks: list[PlaybookDefinition] = Field(default_factory=list)

_BUSINESS_PROFILE_INSTANCE = None

def get_business_profile() -> BusinessProfile:
    """Load and return the BusinessProfile from kultrxp_brain.yaml or business_profile.yaml."""
    global _BUSINESS_PROFILE_INSTANCE
    if _BUSINESS_PROFILE_INSTANCE is not None:
        return _BUSINESS_PROFILE_INSTANCE

    # Search for kultrxp_brain.yaml or business_profile.yaml
    root_dir = Path(__file__).resolve().parent.parent.parent
    profile_path = root_dir / "kultrxp_brain.yaml"

    if not profile_path.exists():
        profile_path = root_dir / "business_profile.yaml"
        if not profile_path.exists():
            profile_path = root_dir / "business_profile.example.yaml"
            if not profile_path.exists():
                raise FileNotFoundError(
                    "No valid configuration (kultrxp_brain.yaml or business_profile.yaml) was found."
                )

    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        data = {}

    _BUSINESS_PROFILE_INSTANCE = BusinessProfile(**data)
    return _BUSINESS_PROFILE_INSTANCE
