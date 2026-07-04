"""Social Media enrichment provider."""

from __future__ import annotations

from typing import Any

from agents.researcher.enrichment_providers.base import BaseEnrichmentProvider


class SocialEnrichmentProvider(BaseEnrichmentProvider):
    """
    Simulates fetching public social growth indicators.
    """

    @property
    def name(self) -> str:
        return "social"

    async def enrich(
        self,
        company_name: str,
        domain: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        co_clean = company_name.strip()
        co_slug = co_clean.lower().replace(" ", "").replace(".", "")
        posts = [
            f"We are hiring! Looking for engineers to join our fast-growing team at {co_clean}.",
            f"Excited to share that {co_clean} hit a new customer milestone today!",
        ]
        return {
            "provider_name": self.name,
            "raw_evidence": {
                "recent_posts": posts,
                "social_metrics": {
                    "linkedin_followers_growth_pct": 18.5,
                    "linkedin_followers_count": 12500,
                }
            },
            "insights": [
                {
                    "text": f"LinkedIn followers growth of 18.5% indicating strong brand expansion for {co_clean}.",
                    "source_url": f"https://linkedin.com/company/{co_slug}"
                },
                {
                    "text": f"Recent social post: {posts[0]}",
                    "source_url": f"https://linkedin.com/company/{co_slug}/posts/1"
                }
            ]
        }
