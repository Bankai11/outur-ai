"""Consolidated contact discovery provider."""

from __future__ import annotations

import asyncio
from typing import Any

from agents.researcher.providers.base import BaseContactProvider
from core.services.search.tavily_provider import TavilySearchProvider
from core.logger import get_logger

log = get_logger(__name__)

class ConsolidatedContactProvider(BaseContactProvider):
    """
    Discovers contacts by querying Tavily for leadership/team info,
    then doing a single Gemini inference on the combined search results.
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.search_provider = TavilySearchProvider()

    @property
    def name(self) -> str:
        return "consolidated_contact"

    def build_prompt(self, company_name: str, domain: str | None = None, **kwargs: Any) -> str:
        search_results = kwargs.get("search_results", [])
        
        domain_str = f" ({domain})" if domain else ""
        prompt = (
            f"You are a sales researcher looking for decision makers at '{company_name}'{domain_str}.\n"
            f"Focus on identifying executives, founders, HR leadership, and hiring managers.\n\n"
            f"Below are the raw search results for this company's team and leadership:\n"
        )
        
        for res in search_results:
            prompt += f"- Title: {res.get('title')}\n  URL: {res.get('url')}\n  Content: {res.get('content')}\n\n"
            
        prompt += (
            "Extract a list of valid contacts from the search results above.\n"
            "You MUST provide strict evidence (the source URL from the context) for each contact.\n"
            "If you cannot find any people in the context, return an empty array."
        )
        
        return prompt

    async def discover_contacts(self, **kwargs: Any) -> list[dict[str, Any]]:
        # 1. Fetch search results deterministicly via Tavily
        company_name = kwargs.get("company_name", "")
        domain = kwargs.get("domain", "")
        
        query = f'"{company_name}" {domain} "leadership" OR "team" OR "careers" OR "founders"'
        
        log.info(f"ConsolidatedContactProvider: Searching Tavily for {company_name} contacts...")
        search_results = await self.search_provider.search(query, limit=10)
        
        kwargs["search_results"] = search_results
        
        # 2. Call the base class logic, which will use build_prompt, cache, and LLM
        return await super().discover_contacts(**kwargs)
        
    async def _execute_llm_with_retry(self, prompt: str) -> Any:
        # Override to turn OFF use_search_grounding, since we injected Tavily results
        from core.llm.factory import get_llm_provider
        from agents.researcher.providers.base import CONTACTS_SCHEMA
        from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential
        
        llm = get_llm_provider()
        
        retryer = AsyncRetrying(
            stop=stop_after_attempt(self.config.retry_limit),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        
        async for attempt in retryer:
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    self.metrics.retries += 1
                    
                res = await llm.generate_json(
                    prompt=prompt,
                    schema=CONTACTS_SCHEMA,
                    use_search_grounding=False,  # OFF to save quota!
                    timeout=float(self.config.timeout_ms) / 1000.0
                )
                return res
