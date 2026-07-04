"""News enrichment provider."""

from __future__ import annotations

from typing import Any

from agents.researcher.enrichment_providers.base import BaseEnrichmentProvider


class NewsEnrichmentProvider(BaseEnrichmentProvider):
    """
    Simulates fetching public news/press releases for a company.
    """

    @property
    def name(self) -> str:
        return "news"

    async def enrich(
        self,
        company_name: str,
        domain: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        co_clean = company_name.strip()
        co_domain = domain or "company.com"
        headlines = [
            f"{co_clean} announces new AI integrations and partnerships",
            f"{co_clean} expands its operations in North America and EMEA",
            f"How {co_clean} is solving modern SaaS scalability challenges",
        ]
        return {
            "provider_name": self.name,
            "raw_evidence": {
                "news_headlines": headlines
            },
            "insights": [
                {
                    "text": h,
                    "source_url": f"https://{co_domain}/news/{i + 1}"
                }
                for i, h in enumerate(headlines)
            ]
        }
