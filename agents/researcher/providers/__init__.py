"""Providers package for Researcher contact discovery agent."""

from __future__ import annotations

from agents.researcher.providers.base import BaseContactProvider
from agents.researcher.providers.careers_page import CareersPageProvider
from agents.researcher.providers.company_website import CompanyWebsiteProvider
from agents.researcher.providers.linkedin_contacts import LinkedInContactsProvider

PROVIDERS: list[BaseContactProvider] = [
    CareersPageProvider(),
    LinkedInContactsProvider(),
    CompanyWebsiteProvider(),
]

__all__ = [
    "BaseContactProvider",
    "CareersPageProvider",
    "LinkedInContactsProvider",
    "CompanyWebsiteProvider",
    "PROVIDERS",
]
