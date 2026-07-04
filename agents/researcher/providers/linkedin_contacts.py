"""LinkedIn Contacts discovery provider."""

from __future__ import annotations

from typing import Any

from agents.researcher.providers.base import BaseContactProvider


class LinkedInContactsProvider(BaseContactProvider):
    """
    Discovers contacts by querying LinkedIn people searches.
    """

    @property
    def name(self) -> str:
        return "linkedin_contacts"

    def build_prompt(self, company_name: str, domain: str | None = None, **kwargs: Any) -> str:
        domain_str = f" ({domain})" if domain else ""
        return (
            f"Perform a LinkedIn people search for employees currently working at '{company_name}'{domain_str}. "
            "Focus on leadership, HR, or relevant hiring managers. "
            "Provide strict evidence for each."
        )

