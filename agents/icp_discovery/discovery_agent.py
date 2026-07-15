import json
from typing import List, Dict, Any

from agents.icp_discovery.schema import CampaignRequirements, RankedProspectList, RankedCompany
from core.llm import get_llm_provider
from core.logger import get_logger
from core.services.search.tavily_provider import TavilySearchProvider

log = get_logger(__name__)

DISCOVERY_QUERY_PROMPT = """
You are an expert sales prospector. 
Given the following campaign requirements, generate 3 highly targeted search queries that can be used to find matching companies on the web.
The search queries should focus on finding companies that fit the ICP (e.g., "fastest growing {{industry}} companies", "top {{industry}} companies hiring {{role}}", etc).

Campaign Requirements:
{requirements}

Respond ONLY with a JSON array of 3 string queries.
"""

RANKING_PROMPT = """
You are a senior sales strategist evaluating a list of discovered companies against an Ideal Customer Profile (ICP).

ICP / Campaign Requirements:
{requirements}

For each of the following raw company descriptions found via search, evaluate whether they are a good fit for this campaign.
Provide a Lead Score (0-100) and an ICP Match Score (0-100).
Extract any buying signals or growth signals mentioned.
Provide a confidence score (0.0 to 1.0) on your assessment and a detailed reason for selection (or rejection).

Raw Companies:
{companies_json}

Ensure you output EXACTLY in the schema requested. Return ONLY the JSON object conforming to the RankedProspectList schema.
"""

class ICPDiscoveryAgent:
    """
    Finds and scores companies based on Campaign Requirements before they are saved to the database.
    """
    def __init__(self):
        self.llm = get_llm_provider()
        self.search_provider = TavilySearchProvider()

    async def discover_and_rank(self, requirements: CampaignRequirements, limit: int = 10) -> List[RankedCompany]:
        """
        Discovers prospects using web search and ranks them against the ICP.
        """
        log.info("Starting ICP Discovery", reqs=requirements.model_dump())

        # 1. Generate Search Queries
        query_prompt = DISCOVERY_QUERY_PROMPT.format(requirements=requirements.model_dump_json(indent=2))
        try:
            queries_json = await self.llm.generate_json(query_prompt, {"type": "array", "items": {"type": "string"}})
            queries = queries_json if isinstance(queries_json, list) else []
            if not queries:
                # Fallback query
                queries = [f"top {requirements.industry or 'tech'} companies"]
        except Exception as e:
            log.warning("Failed to generate search queries", error=str(e))
            queries = [f"top {requirements.industry or 'tech'} companies"]

        # 2. Discover Prospects
        raw_companies = []
        for query in queries[:3]:
            try:
                results = await self.search_provider.search(query, limit=10)
                raw_companies.extend(results)
            except Exception as e:
                log.error("Search failed for query", query=query, error=str(e))

        if not raw_companies:
            log.warning("No companies discovered by search provider.")
            return []
            
        # Deduplicate basic search results by URL
        seen_urls = set()
        unique_raw = []
        for rc in raw_companies:
            url = rc.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_raw.append(rc)
                
        # 3. ICP Ranking
        ranking_prompt = RANKING_PROMPT.format(
            requirements=requirements.model_dump_json(indent=2),
            companies_json=json.dumps(unique_raw[:20], indent=2)  # Cap to avoid token limits
        )
        
        try:
            # We use RankedProspectList schema
            schema = RankedProspectList.model_json_schema()
            ranked_json = await self.llm.generate_json(ranking_prompt, schema)
            
            if not ranked_json or "companies" not in ranked_json:
                log.error("Failed to parse ranked companies JSON.")
                return []
                
            ranked_prospects = [RankedCompany(**c) for c in ranked_json["companies"]]
        except Exception as e:
            log.error("Failed during ICP Ranking", error=str(e))
            return []

        # 4. Company Selection (Filtering)
        selected = []
        for prospect in ranked_prospects:
            if prospect.confidence < requirements.min_confidence:
                continue
            if prospect.icp_match_score < requirements.min_icp_score:
                continue
            if prospect.industry and prospect.industry in requirements.exclude_industries:
                continue
                
            selected.append(prospect)
            
        # Sort by ICP match score and lead score
        selected.sort(key=lambda x: (x.icp_match_score, x.lead_score), reverse=True)
        
        final_list = selected[:limit]
        log.info("ICP Discovery completed", discovered=len(final_list))
        return final_list
