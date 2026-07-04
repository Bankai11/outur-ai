"""Enrichment Agent — STUB. Enriches company and contact records with HR, funding, and tech stack data."""
from __future__ import annotations
from core.logger import get_logger
log = get_logger(__name__)

class EnrichmentAgent:
    """Enriches companies with HR, funding, and tech stack data. Status: STUB."""
    agent_name: str = "enrichment"
    def __init__(self) -> None:
        log.debug("EnrichmentAgent initialised (stub)", agent=self.agent_name)
    async def run(self, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError("EnrichmentAgent.run() not yet implemented.")
