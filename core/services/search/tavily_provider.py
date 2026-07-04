import os
import httpx
from typing import List, Dict, Any
from core.services.search.base import SearchProvider
from core.logger import get_logger

logger = get_logger(__name__)

class TavilySearchProvider(SearchProvider):
    """
    Real search provider using Tavily Search API.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("Tavily API key not found. Returning empty results.")
            return []
            
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
