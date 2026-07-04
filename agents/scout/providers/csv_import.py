"""Manual CSV Import discovery provider."""

from __future__ import annotations

import csv
import io
import os
from typing import Any

from agents.scout.providers.base import BaseDiscoveryProvider
from core.logger import get_logger

log = get_logger(__name__)


class ManualCSVImportProvider(BaseDiscoveryProvider):
    """
    Parses and imports company leads from a CSV file path or raw CSV string content.
    """

    @property
    def name(self) -> str:
        return "manual_csv"

    def build_prompt(self, **kwargs: Any) -> str:
        return ""

    async def discover(
        self,
        industry: str | None = None,
        location: str | None = None,
        company_size: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        csv_content = kwargs.get("csv_content")
        csv_file = kwargs.get("csv_file")

        if not csv_content and csv_file:
            if os.path.exists(csv_file):
                log.info("Reading CSV from file path", path=csv_file)
                with open(csv_file, mode="r", encoding="utf-8") as f:
                    csv_content = f.read()
            else:
                log.error("CSV file not found", path=csv_file)
                raise FileNotFoundError(f"CSV file not found at: {csv_file}")

        if not csv_content:
            log.warning("No CSV content or file provided for Manual CSV Import")
            return []

        # Parse CSV content
        results = []
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        
        # Mapping variations of headers to standardized keys
        header_mapping = {
            "name": ("name", "company name", "company", "title", "organization"),
            "website": ("website", "url", "domain", "company website", "link"),
            "linkedin_url": ("linkedin_url", "linkedin", "linkedin url", "linkedinurl", "linkedin page"),
            "industry": ("industry", "sector", "vertical"),
            "location": ("location", "city", "address", "geography", "country"),
            "careers_page": ("careers_page", "careers", "jobs", "careers url", "careerspage", "careers page"),
        }

        for row in reader:
            normalized: dict[str, Any] = {}
            for target_key, variations in header_mapping.items():
                for cell_key, cell_val in row.items():
                    if cell_key and cell_key.lower().strip() in variations:
                        val = cell_val.strip() if cell_val else ""
                        if val:
                            normalized[target_key] = val
                        break
            
            # Ensure company has at least a name
            if "name" in normalized and normalized["name"]:
                normalized["source"] = self.name
                results.append(normalized)

        log.info("Parsed CSV successfully", parsed_count=len(results))
        return results
