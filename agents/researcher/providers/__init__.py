"""Providers package for Researcher contact discovery agent."""

from __future__ import annotations

from agents.researcher.providers.base import BaseContactProvider
from agents.researcher.providers.consolidated_contact import ConsolidatedContactProvider

PROVIDERS: list[BaseContactProvider] = [
    ConsolidatedContactProvider(),
]

__all__ = [
    "BaseContactProvider",
    "ConsolidatedContactProvider",
    "PROVIDERS",
]
