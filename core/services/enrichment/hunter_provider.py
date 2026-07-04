import os
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from core.services.enrichment.base import EnrichmentProvider
from core.logger import get_logger

logger = get_logger(__name__)

class HunterEnrichmentProvider(EnrichmentProvider):
    """
    Real enrichment provider using Hunter.io's Domain Search API to find role-based contacts.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("HUNTER_API_KEY")
        self.base_url = "https://api.hunter.io/v2"

    async def find_contact(self, domain: str, job_title: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("Hunter API key not found. Returning no contact.")
            return None
            
        params = {
            "domain": domain,
            "department": "hr", # A common grouping, although Hunter allows full-text search too depending on the endpoint.
            "type": "personal",
            "api_key": self.api_key,
            "limit": 10
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/domain-search", params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Filter by job title keyword match
                emails = data.get("data", {}).get("emails", [])
                
                # Naive matching for the target job title
                best_match = None
                for email_data in emails:
                    position = email_data.get("position", "")
                    if position and any(word.lower() in position.lower() for word in job_title.split()):
                        best_match = email_data
                        break
                        
                if not best_match and emails:
                    # If we don't find a perfect title match, we'll take the top HR email if any
                    best_match = emails[0]
                    
                if best_match:
                    return {
                        "full_name": f"{best_match.get('first_name', '')} {best_match.get('last_name', '')}".strip(),
                        "job_title": best_match.get("position", "HR Contact"),
                        "email": best_match.get("value"),
                        "linkedin_url": best_match.get("linkedin"),
                        "confidence_score": best_match.get("confidence", 50),
                        "source_url": "https://hunter.io",
                        "source_type": "hunter_domain_search",
                        "retrieved_at": datetime.utcnow().isoformat()
                    }
                    
                return None
                
        except Exception as e:
            logger.error(f"Hunter enrichment failed for {domain}: {e}")
            return None
