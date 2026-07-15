import re
from typing import Any
from agents.enrichment.validation.schema import STANDARD_INDUSTRIES, STANDARD_FUNDING_STAGES

class EnrichmentNormalizer:
    """Normalizes raw LLM output values."""
    
    @staticmethod
    def normalize_employee_count(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # Extract numbers
            numbers = [int(n) for n in re.findall(r'\d+', value.replace(',', ''))]
            if not numbers:
                return None
            if len(numbers) == 1:
                return numbers[0]
            # If range, return average
            return sum(numbers) // len(numbers)
        return None

    @staticmethod
    def normalize_funding_amount(value: Any) -> str | None:
        if not value:
            return None
        value_str = str(value).strip().upper()
        # Basic cleanup: remove spaces around symbols
        value_str = value_str.replace(" ", "")
        if not value_str.startswith("$"):
            value_str = "$" + value_str
        return value_str

    @staticmethod
    def normalize_industry(value: Any) -> str | None:
        if not value:
            return None
        value_str = str(value).strip()
        if not value_str:
            return None
        # Fuzzy match to standard industries
        for ind in STANDARD_INDUSTRIES:
            if ind.lower() in value_str.lower() or value_str.lower() in ind.lower():
                return ind
        return value_str # Fallback to raw if not matched, to preserve data

    @staticmethod
    def normalize_funding_stage(value: Any) -> str | None:
        if not value:
            return None
        value_str = str(value).strip()
        if not value_str:
            return None
        for stage in STANDARD_FUNDING_STAGES:
            if stage.lower() in value_str.lower() or value_str.lower() in stage.lower():
                return stage
        return value_str

    @staticmethod
    def normalize_linkedin_url(value: Any) -> str | None:
        if not value:
            return None
        url = str(value).strip()
        if "linkedin.com" in url:
            if not url.startswith("http"):
                url = "https://" + url
            return url
        return None

    @staticmethod
    def normalize(data: dict[str, Any]) -> dict[str, Any]:
        """Normalize the raw data dictionary in place where possible."""
        if not isinstance(data, dict):
            return data
            
        if "company_enrichment" in data and isinstance(data["company_enrichment"], dict):
            comp = data["company_enrichment"]
            if "employee_count_verification" in comp:
                comp["employee_count_verification"] = EnrichmentNormalizer.normalize_employee_count(comp["employee_count_verification"])
            if "funding_amount" in comp:
                comp["funding_amount"] = EnrichmentNormalizer.normalize_funding_amount(comp["funding_amount"])
            if "industry" in comp:
                comp["raw_industry"] = comp["industry"]
                comp["industry"] = EnrichmentNormalizer.normalize_industry(comp["industry"])
            if "funding_stage" in comp:
                comp["funding_stage"] = EnrichmentNormalizer.normalize_funding_stage(comp["funding_stage"])
            if "technologies_used" in comp:
                comp["raw_technologies_used"] = comp["technologies_used"]
                # For now just keep them as is, but we store the raw
            if "buying_signals" in comp:
                comp["raw_buying_signals"] = comp["buying_signals"]
            
            if "social_profiles" in comp and isinstance(comp["social_profiles"], dict):
                if "linkedin" in comp["social_profiles"]:
                    comp["social_profiles"]["linkedin"] = EnrichmentNormalizer.normalize_linkedin_url(comp["social_profiles"]["linkedin"])

        if "contact_enrichment" in data and isinstance(data["contact_enrichment"], dict):
            for cid, cont in data["contact_enrichment"].items():
                if isinstance(cont, dict):
                    if "linkedin" in cont:
                        cont["linkedin"] = EnrichmentNormalizer.normalize_linkedin_url(cont["linkedin"])
                        
        return data
