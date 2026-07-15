import pytest
import uuid
from agents.campaign_qa.campaign_qa_engine import CampaignQAEngine
from core.models.company import Company
from core.models.contact import Contact
from core.models.sales_intelligence import SalesIntelligenceProfile

@pytest.fixture
def mock_company():
    return Company(id=uuid.uuid4(), name="Test Corp")

@pytest.fixture
def mock_contact():
    return Contact(id=uuid.uuid4(), company_id=uuid.uuid4(), full_name="John Doe", job_title="CEO", email="john@test.com")

@pytest.fixture
def mock_profile(mock_company):
    return SalesIntelligenceProfile(
        company_id=mock_company.id,
        executive_summary="Test corp makes AI.",
        pain_points=[{"pain_point": "Scaling teams"}],
        recent_news=[{"title": "Test Corp acquires startup"}],
        hiring_signals=[{"insight": "Hiring 10 engineers"}]
    )

@pytest.mark.asyncio
async def test_campaign_qa_engine_success(mock_company, mock_contact, mock_profile):
    """Test the QA engine passes a good email."""
    qa_engine = CampaignQAEngine()
    
    class MockLLM:
        async def generate_json(self, prompt, schema):
            return {
                "overall_score": 90,
                "accuracy_score": 100,
                "personalization_score": 90,
                "grammar_score": 95,
                "cta_score": 85,
                "tone_score": 90,
                "hallucination_score": 100,
                "issues": [],
                "recommendations": [],
                "approved": True
            }
            
    qa_engine.llm = MockLLM()
    report = await qa_engine.evaluate_email(
        "Subject: Quick Chat",
        "Hi John, saw Test Corp acquired a startup. Let's chat.",
        mock_contact,
        mock_company,
        mock_profile
    )
    
    assert report["approved"] is True
    assert report["hallucination_score"] == 100
    assert len(report["issues"]) == 0

@pytest.mark.asyncio
async def test_campaign_qa_engine_hallucination_failure(mock_company, mock_contact, mock_profile):
    """Test the QA engine fails an email with hallucinations."""
    qa_engine = CampaignQAEngine()
    
    class MockLLM:
        async def generate_json(self, prompt, schema):
            return {
                "overall_score": 40,
                "accuracy_score": 30,
                "personalization_score": 50,
                "grammar_score": 95,
                "cta_score": 85,
                "tone_score": 90,
                "hallucination_score": 10,
                "issues": ["Fabricated $100M funding round"],
                "recommendations": ["Remove the funding claim."],
                "approved": False
            }
            
    qa_engine.llm = MockLLM()
    report = await qa_engine.evaluate_email(
        "Subject: Congrats on $100M",
        "Hi John, congrats on the $100M funding round.",
        mock_contact,
        mock_company,
        mock_profile
    )
    
    assert report["approved"] is False
    assert report["hallucination_score"] == 10
    assert "Fabricated $100M funding round" in report["issues"]
