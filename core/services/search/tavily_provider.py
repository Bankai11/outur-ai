import os
import httpx
from typing import List, Dict, Any
from core.logger import get_logger

logger = get_logger(__name__)

class TavilySearchProvider:
    """
    Real search provider using Tavily Search API.
    """
    
    def __init__(self, api_key: str = None):
        from core.config.settings import get_settings
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key
        self.base_url = "https://api.tavily.com/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        from core.config import get_settings
        settings = get_settings()
        if settings.app_env == "testing":
            return [
                {
                    "title": "Stripe - Hiring developers",
                    "url": "https://stripe.com",
                    "content": "Stripe is scaling operations and hiring backend engineers.",
                    "score": 1.0
                },
                {
                    "title": "Plaid - Hiring PMs",
                    "url": "https://plaid.com",
                    "content": "Plaid is looking for experienced product managers.",
                    "score": 0.9
                }
            ]

        if not self.api_key:
            logger.warning("Tavily API key not found. Returning mock results for testing.")
            return [
                {"title": "Acme SaaS", "url": "https://acmesaas.com", "content": "Acme SaaS is a fast-growing B2B software company in the HR tech space, recently hiring 50 engineers."},
                {"title": "Global Tech Services", "url": "https://globaltech.io", "content": "An IT services firm scaling up their operations and transitioning to remote-first."},
                {"title": "HealthPlus", "url": "https://healthplus.org", "content": "Healthcare provider dealing with high burnout, looking for better retention strategies."},
                {"title": "Beta Retail", "url": "https://betaretail.com", "content": "A retail chain opening new stores, but not very focused on remote work."},
                {"title": "Alpha Analytics", "url": "https://alpha-analytics.ai", "content": "Fast growing tech startup in the data space. Scaling quickly and hiring remotely."},
                {"title": "Legacy Finance", "url": "https://legacyfinance.com", "content": "Old traditional bank mandating return to office for all employees."},
                {"title": "ScaleUp Inc", "url": "https://scaleup.io", "content": "ScaleUp is growing its headcount by 200% this year, focusing on company culture."},
                {"title": "MediCare Tech", "url": "https://medicaretech.com", "content": "Healthcare tech company looking to improve employee onboarding for clinical staff."},
                {"title": "CloudWorks", "url": "https://cloudworks.net", "content": "SaaS infrastructure provider that just hired a new Chief People Officer."},
                {"title": "DevShop Pro", "url": "https://devshoppro.com", "content": "IT Services company struggling with employee retention in a competitive market."}
            ]
            
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": limit
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for result in data.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 1.0)
                    })
                return results
                
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
