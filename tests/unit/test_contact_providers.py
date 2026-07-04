"""Unit tests for contact discovery providers."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from agents.researcher.providers.careers_page import CareersPageProvider
from core.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    def __init__(self, return_val=None, side_effect=None):
        self.return_val = return_val
        self.side_effect = side_effect
        self.call_count = 0

    async def generate_json(self, prompt, schema, use_search_grounding=False, **kwargs):
        self.call_count += 1
        if self.side_effect:
            if isinstance(self.side_effect, list):
                eff = self.side_effect.pop(0)
                if isinstance(eff, Exception):
                    raise eff
                return eff
            raise self.side_effect
        return self.return_val


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear sqlite cache table before each test to prevent cache pollution."""
    import sqlite3
    from core.utils.cache import get_cache
    db_path = get_cache().db_path
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM llm_cache")
    yield
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM llm_cache")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_careers_page_provider_no_data() -> None:
    """
    Test that provider returns empty list when LLM returns no results.
    """
    mock_llm = MockLLMProvider(return_val=[])
    with patch("agents.researcher.providers.base.get_llm_provider", return_value=mock_llm):
        provider = CareersPageProvider()
        results = await provider.discover_contacts(company_name="Acme Corp")
        
        assert len(results) == 0
        assert mock_llm.call_count == 1
        assert provider.metrics.failures == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_careers_page_provider_native_confidence() -> None:
    """
    Test provider calculates confidence natively based on evidence and drops bad records.
    """
    mock_llm_response = [
        {
            "full_name": "Jane Doe",
            "job_title": "Head of Talent",
            "email": "jane@acme.com",
            "evidence": [
                {"source_url": "https://acme.com/team", "source_type": "Website"},
                {"source_url": "https://linkedin.com/in/jane", "source_type": "LinkedIn"}
            ]
        },
        {
            "full_name": "John Smith",
            "job_title": "Recruiter",
            "evidence": [] # No evidence, should be dropped
        }
    ]
    
    mock_llm = MockLLMProvider(return_val=mock_llm_response)
    with patch("agents.researcher.providers.base.get_llm_provider", return_value=mock_llm):
        provider = CareersPageProvider()
        results = await provider.discover_contacts(company_name="Acme Corp")
        
        # Only 1 valid record should survive the strict evidence check
        assert len(results) == 1
        contact = results[0]
        
        assert contact["full_name"] == "Jane Doe"
        assert contact["source"] == "careers_page"
        assert "confidence_score" in contact
        # Website (+25) + LinkedIn (+20) + Multiple Domains (+10) = 55
        assert contact["confidence_score"] == 55
        
        # Test Metrics
        assert provider.metrics.average_confidence == 55.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_caching() -> None:
    """Test that LLM calls are cached and hit on subsequent calls."""
    mock_llm_response = [
        {
            "full_name": "Cached Contact",
            "job_title": "Manager",
            "evidence": [{"source_url": "https://cached.com", "source_type": "Website"}]
        }
    ]
    
    mock_llm = MockLLMProvider(return_val=mock_llm_response)
    with patch("agents.researcher.providers.base.get_llm_provider", return_value=mock_llm):
        provider = CareersPageProvider()
        
        # First call (cache miss)
        results1 = await provider.discover_contacts(company_name="Cache Corp")
        assert len(results1) == 1
        assert mock_llm.call_count == 1
        
        # Second call (cache hit)
        results2 = await provider.discover_contacts(company_name="Cache Corp")
        assert len(results2) == 1
        assert results2[0]["full_name"] == "Cached Contact"
        assert mock_llm.call_count == 1 # Still 1!
