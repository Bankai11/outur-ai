from typing import Any
from agents.enrichment.models import ConfidenceMetadata
from agents.enrichment.validation.schema import is_valid_url, is_valid_linkedin

class ConfidenceEvaluator:
    """Evaluates and assigns confidence scores to enrichment fields."""

    @staticmethod
    def evaluate_company(comp: dict[str, Any]) -> dict[str, ConfidenceMetadata]:
        scores = {}
        
        # Employee Count
        emp_count = comp.get("employee_count_verification")
        if emp_count is not None:
            if isinstance(emp_count, int) and emp_count > 0:
                scores["employee_count_verification"] = ConfidenceMetadata(score=0.95, reason="Valid integer format", method="heuristic")
            else:
                scores["employee_count_verification"] = ConfidenceMetadata(score=0.4, reason="Format does not strictly match expected integer", method="heuristic")
        else:
            scores["employee_count_verification"] = ConfidenceMetadata(score=0.0, reason="Missing field", method="heuristic")

        # Funding
        funding = comp.get("funding_amount")
        if funding:
            if "$" in str(funding):
                scores["funding_amount"] = ConfidenceMetadata(score=0.9, reason="Valid funding string format", method="heuristic")
            else:
                scores["funding_amount"] = ConfidenceMetadata(score=0.6, reason="Missing standard currency format", method="heuristic")
        else:
            scores["funding_amount"] = ConfidenceMetadata(score=0.0, reason="Missing field", method="heuristic")

        # LinkedIn
        social = comp.get("social_profiles", {})
        if social and isinstance(social, dict) and "linkedin" in social:
            if is_valid_linkedin(social.get("linkedin", "")):
                scores["linkedin"] = ConfidenceMetadata(score=0.98, reason="Valid LinkedIn format", method="heuristic")
            else:
                scores["linkedin"] = ConfidenceMetadata(score=0.3, reason="Invalid LinkedIn URL format", method="heuristic")
        else:
            scores["linkedin"] = ConfidenceMetadata(score=0.0, reason="Missing social profile", method="heuristic")

        # Industry
        industry = comp.get("industry")
        if industry:
            scores["industry"] = ConfidenceMetadata(score=0.85, reason="Present and mapped", method="heuristic")
        else:
            scores["industry"] = ConfidenceMetadata(score=0.0, reason="Missing field", method="heuristic")
        
        # Revenue
        revenue = comp.get("revenue_estimate")
        if revenue:
            scores["revenue_estimate"] = ConfidenceMetadata(score=0.75, reason="Present", method="heuristic")
        else:
            scores["revenue_estimate"] = ConfidenceMetadata(score=0.0, reason="Missing field", method="heuristic")

        # Overall Company Score
        weights = {
            "employee_count_verification": 0.3,
            "industry": 0.2,
            "linkedin": 0.2,
            "funding_amount": 0.15,
            "revenue_estimate": 0.15
        }
        overall = sum(scores.get(k, ConfidenceMetadata(score=0.0)).score * w for k, w in weights.items())
        scores["overall"] = ConfidenceMetadata(score=round(overall, 2), reason="Weighted average of all signals", method="heuristic")
        return scores

    @staticmethod
    def evaluate_contact(cont: dict[str, Any]) -> dict[str, ConfidenceMetadata]:
        scores = {}

        # Email
        email = cont.get("work_email")
        if email and "@" in str(email):
            if cont.get("email_verification_status") == "Verified":
                scores["work_email"] = ConfidenceMetadata(score=0.99, reason="Valid email and explicitly verified", method="heuristic")
            else:
                scores["work_email"] = ConfidenceMetadata(score=0.7, reason="Valid email format but not explicitly verified", method="heuristic")
        else:
            scores["work_email"] = ConfidenceMetadata(score=0.0, reason="Missing or invalid email", method="heuristic")

        # LinkedIn
        linkedin = cont.get("linkedin")
        if is_valid_linkedin(str(linkedin)):
            scores["linkedin"] = ConfidenceMetadata(score=0.95, reason="Valid LinkedIn format", method="heuristic")
        elif linkedin:
            scores["linkedin"] = ConfidenceMetadata(score=0.2, reason="Invalid LinkedIn URL format", method="heuristic")
        else:
            scores["linkedin"] = ConfidenceMetadata(score=0.0, reason="Missing field", method="heuristic")

        # Role
        seniority = cont.get("seniority")
        if seniority:
            scores["seniority"] = ConfidenceMetadata(score=0.85, reason="Present", method="heuristic")
        else:
            scores["seniority"] = ConfidenceMetadata(score=0.0, reason="Missing field", method="heuristic")

        weights = {
            "work_email": 0.5,
            "linkedin": 0.3,
            "seniority": 0.2
        }
        overall = sum(scores.get(k, ConfidenceMetadata(score=0.0)).score * w for k, w in weights.items())
        scores["overall"] = ConfidenceMetadata(score=round(overall, 2), reason="Weighted average of contact signals", method="heuristic")
        return scores

    @staticmethod
    def evaluate(data: dict[str, Any]) -> dict[str, Any]:
        """Inject confidence scores into the dictionary."""
        if not isinstance(data, dict):
            return data

        if "company_enrichment" in data and isinstance(data["company_enrichment"], dict):
            # We have to convert ConfidenceMetadata back to dictionaries for validation mapping
            scores_dict = ConfidenceEvaluator.evaluate_company(data["company_enrichment"])
            data["company_enrichment"]["confidence_scores"] = {k: v.model_dump() for k, v in scores_dict.items()}

        if "contact_enrichment" in data and isinstance(data["contact_enrichment"], dict):
            for cid, cont in data["contact_enrichment"].items():
                if isinstance(cont, dict):
                    scores_dict = ConfidenceEvaluator.evaluate_contact(cont)
                    cont["confidence_scores"] = {k: v.model_dump() for k, v in scores_dict.items()}

        return data
