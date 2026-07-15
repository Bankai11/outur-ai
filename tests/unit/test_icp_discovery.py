import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.icp_discovery.discovery_agent import ICPDiscoveryAgent
from agents.icp_discovery.schema import CampaignRequirements

@pytest.mark.asyncio
async def test_icp_discovery_success():
    """Test the ICPDiscoveryAgent discovers and filters correctly."""
    agent = ICPDiscoveryAgent()
    
    # Mock LLM provider
    class MockLLM:
        async def generate_json(self, prompt, schema):
            if "DISCOVERY_QUERY_PROMPT" in prompt or "queries" in prompt.lower():
                return ["top SaaS companies"]
            else:
                return {
                    "companies": [
                        {
                            "company_name": "Test Corp",
                            "website": "testcorp.com",
                            "industry": "SaaS",
                            "employee_count": "50-200",
                            "country": "USA",
                            "lead_score": 90,
                            "icp_match_score": 95,
                            "buying_signals": ["Hiring engineers"],
                            "growth_signals": ["Series A"],
                            "confidence": 0.9,
                            "reason_for_selection": "Perfect fit"
                        },
                        {
                            "company_name": "Bad Corp",
                            "website": "badcorp.com",
                            "industry": "Retail",
                            "employee_count": "1-10",
                            "country": "USA",
                            "lead_score": 20,
                            "icp_match_score": 30,
                            "buying_signals": [],
                            "growth_signals": [],
                            "confidence": 0.8,
                            "reason_for_selection": "Wrong industry"
                        }
                    ]
                }
                
    agent.llm = MockLLM()
    
    # Mock Search provider
    class MockSearchProvider:
        async def search(self, query, limit=5):
            return [
                {"title": "Test Corp", "url": "testcorp.com", "content": "Test Corp is a SaaS company."},
                {"title": "Bad Corp", "url": "badcorp.com", "content": "Bad Corp is a retail store."}
            ]
            
    agent.search_provider = MockSearchProvider()
    
    requirements = CampaignRequirements(
        industry="SaaS",
        min_icp_score=50,
        exclude_industries=["Retail"]
    )
    
    results = await agent.discover_and_rank(requirements, limit=10)
    
    assert len(results) == 1
    assert results[0].company_name == "Test Corp"
    assert results[0].icp_match_score == 95
    assert results[0].industry == "SaaS"
