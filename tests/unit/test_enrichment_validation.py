import pytest
from unittest.mock import patch, AsyncMock
from agents.enrichment.validation.validator import ValidationPipeline
from agents.enrichment.models import EnrichmentResult

@pytest.mark.asyncio
async def test_validation_pipeline_normalizes_data():
    raw_data = {
        "company_enrichment": {
            "industry": "Software Dev",
            "employee_count_verification": "150 - 200 employees",
            "funding_amount": "50M",
            "funding_stage": "Series b round",
            "social_profiles": {
                "linkedin": "linkedin.com/company/test"
            }
        },
        "contact_enrichment": {
            "uuid-123": {
                "linkedin": "www.linkedin.com/in/test"
            }
        }
    }
    
    result = await ValidationPipeline.process(raw_data)
    
    assert result.validation_status == "valid"
    assert result.company_enrichment is not None
    assert result.company_enrichment.industry == "Software Development"
    assert result.company_enrichment.employee_count_verification == 175
    assert result.company_enrichment.funding_amount == "$50M"
    assert result.company_enrichment.funding_stage == "Series B"
    assert result.company_enrichment.social_profiles["linkedin"] == "https://linkedin.com/company/test"
    assert result.contact_enrichment["uuid-123"].linkedin == "https://www.linkedin.com/in/test"
    
@pytest.mark.asyncio
async def test_validation_pipeline_computes_confidence():
    raw_data = {
        "company_enrichment": {
            "industry": "Healthcare",
            "employee_count_verification": 50,
            "social_profiles": {"linkedin": "https://linkedin.com/company/health"}
        },
        "contact_enrichment": {
            "uuid-123": {
                "work_email": "test@example.com",
                "email_verification_status": "Verified",
                "linkedin": "https://linkedin.com/in/test",
                "seniority": "VP"
            }
        }
    }
    
    result = await ValidationPipeline.process(raw_data)
    
    # Check Company Confidence
    comp_conf = result.company_enrichment.confidence_scores
    assert comp_conf["employee_count_verification"].score == 0.95
    assert comp_conf["linkedin"].score == 0.98
    assert comp_conf["industry"].score == 0.85
    assert comp_conf["funding_amount"].score == 0.0 # Missing
    assert comp_conf["overall"].score > 0.6
    
    # Check Contact Confidence
    cont_conf = result.contact_enrichment["uuid-123"].confidence_scores
    assert cont_conf["work_email"].score == 0.99
    assert cont_conf["linkedin"].score == 0.95
    assert cont_conf["overall"].score > 0.8

@pytest.mark.asyncio
async def test_validation_pipeline_repairs_json_string():
    raw_data = "```json\n{\"company_enrichment\": {\"industry\": \"Retail\"}}\n```"
    result = await ValidationPipeline.process(raw_data)
    
    assert result.validation_status == "valid"
    assert result.company_enrichment.industry == "Retail"

@pytest.mark.asyncio
@patch("agents.enrichment.validation.repair.get_llm_provider")
async def test_validation_pipeline_llm_self_repair(mock_get_llm):
    # Setup mock LLM
    mock_llm = AsyncMock()
    # It returns a fixed, valid JSON structure
    mock_llm.generate_json.return_value = {
        "company_enrichment": {"industry": "Education"}
    }
    mock_get_llm.return_value = mock_llm

    # A badly formatted dictionary that causes Pydantic schema error
    # (e.g. buying_signals expecting dict but got string)
    raw_data = {
        "company_enrichment": {
            "industry": "Education",
            "buying_signals": "Yes they are hiring" # Schema violation
        }
    }
    
    result = await ValidationPipeline.process(raw_data)
    
    # Should have called LLM to repair
    mock_llm.generate_json.assert_called_once()
    assert result.validation_status == "repaired"
    assert result.company_enrichment.industry == "Education"
    assert "Successfully repaired via LLM." in result.validation_errors

from agents.enrichment.validation.normalizer import EnrichmentNormalizer
from agents.enrichment.validation.repair import EnrichmentRepairer

def test_normalizer_edge_cases():
    # employee_count
    assert EnrichmentNormalizer.normalize_employee_count("garbage") is None
    assert EnrichmentNormalizer.normalize_employee_count("") is None
    
    # funding amount
    assert EnrichmentNormalizer.normalize_funding_amount("unknown") == "$UNKNOWN"
    assert EnrichmentNormalizer.normalize_funding_amount("") is None
    
    # funding stage
    assert EnrichmentNormalizer.normalize_funding_stage("pre-seed") == "Pre-Seed"
    assert EnrichmentNormalizer.normalize_funding_stage("IPO") == "IPO"
    assert EnrichmentNormalizer.normalize_funding_stage("") is None
    
    # industry
    assert EnrichmentNormalizer.normalize_industry("  ") is None
    assert EnrichmentNormalizer.normalize_industry("Artificial Intelligence") == "Artificial Intelligence"
    
    # linkedin
    assert EnrichmentNormalizer.normalize_linkedin_url("invalid_url") is None
    assert EnrichmentNormalizer.normalize_linkedin_url("") is None

@pytest.mark.asyncio
@patch("agents.enrichment.validation.repair.get_llm_provider")
async def test_repairer_llm_exception(mock_get_llm):
    mock_llm = AsyncMock()
    mock_llm.generate_json.side_effect = Exception("API Error")
    mock_get_llm.return_value = mock_llm
    
    result = await EnrichmentRepairer.repair({"invalid": "schema"}, "Bad schema")
    assert result is None
    
@pytest.mark.asyncio
@patch("agents.enrichment.validation.repair.get_llm_provider")
async def test_repairer_bad_json_string(mock_get_llm):
    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = {"fixed": "data"}
    mock_get_llm.return_value = mock_llm
    
    # String that doesn't parse as JSON
    result = await EnrichmentRepairer.repair("This is not JSON", "Format error")
    
    assert result == {"fixed": "data"}
    mock_llm.generate_json.assert_called_once()
