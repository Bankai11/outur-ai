"""Evidence models and confidence calculation logic."""

from __future__ import annotations

from typing import TypedDict, Any
from datetime import datetime


class Evidence(TypedDict):
    """Evidence record for discovered entities."""
    source_url: str
    source_title: str
    source_type: str
    retrieved_at: str


class ConfidenceEngine:
    """
    A modular engine to calculate confidence scores based on weighted signals.
    """
    def __init__(self, weights: dict[str, int] | None = None) -> None:
        """
        Initialize with custom weights or fallback to defaults.
        """
        self.weights = weights or {
            "google_search": 30,
            "website": 25,
            "linkedin": 20,
            "news_article": 15,
            "email_verified": 30,
            "multiple_domains_bonus": 10,
            "unknown_fallback": 10,
        }

    def evaluate(self, evidence_list: list[Evidence | dict[str, Any]], additional_signals: dict[str, bool] | None = None) -> int:
        """
        Evaluate confidence score up to a maximum of 100.
        """
        if not evidence_list and not additional_signals:
            return 0

        score = 0
        domains = set()

        for evidence in evidence_list:
            # Handle both dictionary and typeddict appropriately
            source_type = evidence.get("source_type", "").lower() if isinstance(evidence, dict) else getattr(evidence, "source_type", "").lower()
            source_url = evidence.get("source_url", "").lower() if isinstance(evidence, dict) else getattr(evidence, "source_url", "").lower()
            
            # Add to domains for diversity check
            if source_url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(source_url).netloc
                    if domain:
                        domains.add(domain)
                except Exception:
                    pass

            if "google search" in source_type or "search" in source_type:
                score += self.weights.get("google_search", 30)
            elif "website" in source_type or "company" in source_type:
                score += self.weights.get("website", 25)
            elif "linkedin" in source_type:
                score += self.weights.get("linkedin", 20)
            elif "news" in source_type or "article" in source_type:
                score += self.weights.get("news_article", 15)
            else:
                score += self.weights.get("unknown_fallback", 10)
                
        # Bonus for corroboration across multiple domains
        if len(domains) > 1:
            score += self.weights.get("multiple_domains_bonus", 10)
            
        # Process additional signals
        if additional_signals:
            if additional_signals.get("email_verified"):
                score += self.weights.get("email_verified", 30)

        return min(100, score)


# Backwards compatibility function
_default_engine = ConfidenceEngine()

def calculate_confidence(evidence_list: list[Evidence]) -> int:
    """Calculate confidence score (deprecated: use ConfidenceEngine instead)."""
    return _default_engine.evaluate(evidence_list)
