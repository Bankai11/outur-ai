import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.prospector.agent import AutonomousProspector

# Mock out the API keys and httpx requests
from core.services.search.tavily_provider import TavilySearchProvider
from core.services.enrichment.hunter_provider import HunterEnrichmentProvider
from core.services.verification.hunter_verifier import HunterVerificationProvider
from core.services.email import get_email_provider
from unittest.mock import patch, AsyncMock, MagicMock

async def run_test():
    prospector = AutonomousProspector()
    
    # Let's patch the search to return mock data
    async def mock_search(query, limit=5):
        return [
            {
                "title": "Example SaaS Co - Hiring Now",
                "url": "https://examplesaas.com",
                "content": "We just raised Series A and are rapidly scaling our engineering team in Bangalore.",
                "score": 1.0
            }
        ]
        
    async def mock_enrichment(domain, job_title):
        return {
            "full_name": "Test HR",
            "job_title": "Talent Acquisition Lead",
            "email": "hr@examplesaas.com",
            "confidence_score": 98,
            "source_url": "https://hunter.io/test",
            "source_type": "mock",
            "retrieved_at": "2026-07-02T10:00:00Z"
        }
        
    async def mock_verification(email):
        # Enforce >= 95 and mx_valid
        return True, {
            "status": "valid",
            "score": 99,
            "mx_valid": True,
            "reason": "mock"
        }
        
    prospector.scout.run = AsyncMock(return_value={
        "success": True,
        "data": {
            "companies": [
                {
                    "id": "12345678-1234-5678-1234-567812345678",
                    "domain": "examplesaas.com",
                    "name": "Example SaaS",
                    "industry": "SaaS",
                    "location": "Global",
                }
            ]
        }
    })
    
    prospector.enricher.find_contact = AsyncMock(side_effect=mock_enrichment)
    prospector.verifier.verify_email = AsyncMock(side_effect=mock_verification)
    prospector.email_provider = AsyncMock()
    prospector.email_provider.send_email = AsyncMock(return_value={"success": True, "message_id": "test-msg-123"})
    
    # We actually need a real DB session to create the campaign, companies, contacts, drafts
    # Let's use the real DB, but mock the ScoutAgent's DB writes if we can, or just let it create a campaign
    # Wait, the company ID needs to exist in the DB because of the foreign key on Contact!
    from core.database import async_session_factory
    from core.models.company import Company
    import uuid
    
    async with async_session_factory() as session:
        co = Company(id=uuid.uuid4(), name="Example SaaS", domain="examplesaas2.com", source="web_search")
        session.add(co)
        await session.commit()
        
        prospector.scout.run = AsyncMock(return_value={
            "success": True,
            "data": {
                "companies": [
                    {
                        "id": str(co.id),
                        "domain": co.domain,
                        "name": co.name,
                        "industry": "SaaS",
                        "location": "Global",
                    }
                ]
            }
        })

    print("Running cycle...")
    result = await prospector.run_cycle(industry="SaaS", location="Global", limit=1)
    print("Cycle Result:", result)

if __name__ == "__main__":
    asyncio.run(run_test())
