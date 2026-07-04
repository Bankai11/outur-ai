"""Company Website contact discovery provider."""

from __future__ import annotations

from typing import Any

from agents.researcher.providers.base import BaseContactProvider


class CompanyWebsiteProvider(BaseContactProvider):
    """
    Discovers contacts by querying the company's general website (Team/About pages).
    """

    @property
    def name(self) -> str:
        return "company_website"

    def build_prompt(self, company_name: str, domain: str | None = None, **kwargs: Any) -> str:
        domain_str = f" ({domain})" if domain else ""
        return (
            f"Search the official website, 'About Us', and 'Team' pages of '{company_name}'{domain_str}. "
            "Identify key executives, founders, or department leaders. "
            "Provide strict evidence for each."
        )

