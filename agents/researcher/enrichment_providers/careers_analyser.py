"""Careers analyser enrichment provider."""

from __future__ import annotations

from typing import Any

from agents.researcher.enrichment_providers.base import BaseEnrichmentProvider


class CareersAnalyserProvider(BaseEnrichmentProvider):
    """
    Simulates crawling/analyzing job descriptions for a company.
    """

    @property
    def name(self) -> str:
        return "careers_analyser"

    async def enrich(
        self,
        company_name: str,
        domain: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        co_domain = domain or "company.com"
        roles = [
            "Senior Software Engineer (Backend)",
            "Product Manager, Growth",
            "Developer Advocate",
        ]
        techs = [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "AWS",
        ]
        pains = [
            "Scale backend API performance and handle higher traffic throughput",
            "Optimize conversion rates on user onboarding flow",
        ]
        return {
            "provider_name": self.name,
            "raw_evidence": {
                "open_roles": roles,
                "technologies_found": techs,
                "hiring_pain_points": pains
            },
            "insights": [
                {
                    "text": f"Active hiring identified for roles such as Senior Software Engineer (Backend) and Product Manager.",
                    "source_url": f"https://{co_domain}/careers"
                },
                {
                    "text": f"Tech stack contains Python, FastAPI, PostgreSQL, AWS.",
                    "source_url": f"https://{co_domain}/careers/jobs/eng-1"
                },
                {
                    "text": f"Hiring pain point identified: {pains[0]}",
                    "source_url": f"https://{co_domain}/careers/jobs/eng-1"
                }
            ]
        }
