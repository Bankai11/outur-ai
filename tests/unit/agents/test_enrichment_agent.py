import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from agents.enrichment.agent import EnrichmentAgent
from agents.enrichment.service import EnrichmentService
from agents.enrichment.models import EnrichmentResult, CompanyEnrichment, BuyingSignals
from core.models.company import Company

@pytest.mark.asyncio
async def test_enrichment_agent_success(db_session) -> None:
    agent = EnrichmentAgent()
    
    # Create a real company in DB
    company = Company(
        name="Test Corp",
        website="https://testcorp.com",
        domain="testcorp.com",
        source="scout",
        enrichment_data={}
    )
    db_session.add(company)
    await db_session.commit()
    
    # Mock the enrichment service
    mock_service = AsyncMock(spec=EnrichmentService)
    mock_service.enrich.return_value = EnrichmentResult(
        company_enrichment=CompanyEnrichment(
            industry="Tech",
            buying_signals=BuyingSignals(recent_growth=True)
        ),
        contact_enrichment={},
        raw_data={"test": "data"}
    )
    agent.service = mock_service
    
    result = await agent._execute_agent(
        company_id=company.id,
        company=company,
        session=db_session,
        commit=True
    )
    
    assert result["success"] is True
    assert result["data"]["company_id"] == str(company.id)
    
    # Verify enrichment data was attached to company
    assert company.enrichment_data is not None
    assert company.enrichment_data["industry"] == "Tech"
    assert company.enrichment_data["buying_signals"]["recent_growth"] is True
