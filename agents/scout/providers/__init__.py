"""Providers package for Scout discovery agent."""

from __future__ import annotations

from agents.scout.providers.base import BaseDiscoveryProvider
from agents.scout.providers.csv_import import ManualCSVImportProvider
from agents.scout.providers.web_search import WebSearchProvider

PROVIDERS: list[BaseDiscoveryProvider] = [
    WebSearchProvider(),
    ManualCSVImportProvider(),
]

__all__ = [
    "BaseDiscoveryProvider",
    "WebSearchProvider",
    "ManualCSVImportProvider",
    "PROVIDERS",
]
