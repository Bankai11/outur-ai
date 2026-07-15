import pytest
import uuid
from datetime import datetime

from agents.research.sales_intelligence_engine import SalesIntelligenceEngine
from core.models.sales_intelligence import SalesIntelligenceProfile

@pytest.fixture
def mock_enrichment_data():
    return {
        "news": {
            "insights": [
                {"text": "Acme Corp acquires local HR startup to boost engagement.", "source_url": "https://news.com/acme-hr"}
            ]
        },
        "careers_analyser": {
            "insights": [
                {"text": "Hiring 50 new engineers in Q3.", "source_url": "https://acme.com/careers"}
            ]
        }
    }

@pytest.mark.asyncio
async def test_sales_intelligence_engine_schema(mock_enrichment_data):
    """Test that the engine builds all 4 modules and returns a dictionary matching the schema."""
    engine = SalesIntelligenceEngine()
    
    # We will mock the LLM provider inside the engine to return predictable JSONs
    # so we don't actually hit the LLM in unit tests.
    
    class MockLLM:
        async def generate_json(self, prompt, schema):
            if "Extract factual business context" in prompt:
                return {
                    "executive_summary": "Test Summary",
                    "business_overview": "Test Overview",
                    "business_model": "B2B SaaS",
                    "target_customers": "Enterprise",
                    "products_services": "HR Software",
                    "growth_stage": "Series C",
                    "technology_stack": ["Python", "React"],
                    "hiring_activity": "High",
                    "recent_news": [{"title": "News 1", "url": "http://news"}],
                    "recent_funding": {"amount": "10M", "date": "2023"},
                    "hiring_signals": [{"insight": "Hiring Engineers", "source_url": "http://hire"}],
                    "buying_signals": [{"insight": "Bought new tools", "source_url": "http://buy"}],
                    "digital_transformation_signals": [{"insight": "Moving to cloud", "source_url": "http://cloud"}]
                }
            elif "Senior Sales Analyst" in prompt:
                return {
                    "strategic_initiatives": "Scaling EMEA",
                    "competitive_landscape": "Fragmented",
                    "key_differentiators": "Speed",
                    "potential_decision_makers": [{"title": "CHRO", "reasoning": "Controls HR budget"}],
                    "communication_style": "Direct",
                    "risk_assessment": "Low risk",
                    "sales_opportunity_summary": "High value opp",
                    "pain_points": [
                        {"pain_point": "High turnover", "confidence": 95, "supporting_evidence": "Glassdoor", "reasoning": "Lots of negative reviews"}
                    ]
                }
            elif "platform focusing on:" in prompt:
                return {
                    "product_value_mapping": [
                        {"use_case": "Retention", "value_prop": "Improve engagement", "reasoning": "They have high turnover", "confidence": 90}
                    ]
                }
            elif "actionable outreach intelligence" in prompt:
                return {
                    "outreach_intelligence": {
                        "best_opening_sentence": "Hi,",
                        "relevant_achievement": "News 1",
                        "relevant_pain_point": "High turnover",
                        "recommended_tone": "Casual",
                        "recommended_email_length": "Short",
                        "recommended_cta": "Chat?",
                        "topics_to_avoid": ["Pricing"],
                        "topics_to_emphasize": ["Engagement"]
                    }
                }
            return {}

    engine.llm = MockLLM()
    
    profile_data = await engine.analyze_company("Acme Corp", "acme.com", mock_enrichment_data)
    
    assert profile_data["executive_summary"] == "Test Summary"
    assert profile_data["confidence_score"] == 95
    assert "http://hire" in profile_data["supporting_sources"]
    assert profile_data["product_value_mapping"][0]["use_case"] == "Retention"
    assert profile_data["outreach_intelligence"]["recommended_tone"] == "Casual"

def test_sales_intelligence_profile_model():
    """Test instantiating the SQLAlchemy model."""
    profile = SalesIntelligenceProfile(
        company_id=uuid.uuid4(),
        executive_summary="Testing",
        confidence_score=90
    )
    assert profile.executive_summary == "Testing"
    assert profile.confidence_score == 90
