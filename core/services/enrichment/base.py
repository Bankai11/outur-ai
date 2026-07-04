from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class EnrichmentProvider(ABC):
    """
    Abstract base class for contact enrichment providers.
    """
    
    @abstractmethod
    async def find_contact(self, domain: str, job_title: str) -> Optional[Dict[str, Any]]:
        """
        Find a specific contact at a company by domain and job title/role.
        
        Args:
            domain: The company domain (e.g. 'stripe.com').
            job_title: The target role (e.g. 'Talent Acquisition Lead').
            
        Returns:
            Dictionary with contact info or None if not found.
            Expected keys:
            - full_name (str)
            - job_title (str)
            - email (str)
            - linkedin_url (str, optional)
            - confidence_score (int)
            - source_url (str)
            - source_type (str)
        """
        pass
