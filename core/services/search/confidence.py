"""Confidence scoring engine for merged search results."""

from typing import Any
from core.logger import get_logger

log = get_logger(__name__)


class ConfidenceEngine:
    """
    Calculates unified confidence scores based on multiple weighted signals
    and corroborating evidence sources.
    """
    
    # Base weights for different types of sources
    SOURCE_WEIGHTS = {
        "google": 30,
        "company_website": 25,
        "linkedin": 20,
        "apollo": 15,
        "crunchbase": 15,
        "hunter": 15,
        "glassdoor": 10,
        "builtwith": 10,
        "pdl": 15,
    }
    
    # Bonus for corroboration (multiple independent sources found the same entity)
    CORROBORATION_BONUS_PER_SOURCE = 10
    
    @classmethod
    def calculate_company_confidence(cls, profile: dict[str, Any]) -> int:
        """
        Calculate confidence for a merged company profile.
        """
        evidence = profile.get("evidence", [])
        if not evidence:
            return 0
            
        score = 0
        sources_seen = set()
        
        for ev in evidence:
            source_type = ev.get("source_type", "").lower()
            if source_type and source_type not in sources_seen:
                score += cls.SOURCE_WEIGHTS.get(source_type, 5)
                sources_seen.add(source_type)
                
        # Add corroboration bonus (only for sources after the first one)
        if len(sources_seen) > 1:
            score += (len(sources_seen) - 1) * cls.CORROBORATION_BONUS_PER_SOURCE
            
        # Domain match bonus
        domain = profile.get("domain")
        name = profile.get("name")
        if domain and name:
            # Simple heuristic: if domain contains the name (or vice versa), it's a strong signal
            normalized_name = name.lower().replace(" ", "").replace(",", "").replace(".", "")
            if normalized_name in domain.lower() or domain.lower().split(".")[0] in normalized_name:
                score += 15
                
        return min(100, score)

    @classmethod
    def calculate_contact_confidence(cls, contact: dict[str, Any]) -> int:
        """
        Calculate confidence for a contact.
        Takes into account email verification status if available.
        """
        score = 0
        
        # Base score from the discovery source
        ev = contact.get("source_evidence", {})
        source_type = ev.get("source_type", "").lower()
        score += cls.SOURCE_WEIGHTS.get(source_type, 10)
        
        # Email existence bonus
        email = contact.get("email")
        if email:
            score += 20
            
        # Verification bonus (hooks into Deliverability module later)
        verification_status = contact.get("verification_status")
        if verification_status == "verified":
            score += 50
        elif verification_status == "risky":
            score -= 20
        elif verification_status == "invalid":
            score -= 100
            
        return max(0, min(100, score))
