"""Careers Page contact discovery provider."""

from __future__ import annotations

from typing import Any

from agents.researcher.providers.base import BaseContactProvider


class CareersPageProvider(BaseContactProvider):
    """
    Discovers contacts by querying the company's careers page or job listings.
    """

    @property
    def name(self) -> str:
        return "careers_page"

    def build_prompt(self, company_name: str, domain: str | None = None, **kwargs: Any) -> str:
        domain_str = f" ({domain})" if domain else ""
        return (
            f"Search the careers page, job listings, and 'about us' pages for '{company_name}'{domain_str}. "
            "Identify hiring managers, recruiters, talent acquisition staff, or department heads. "
            "Provide strict evidence for each."
        )

