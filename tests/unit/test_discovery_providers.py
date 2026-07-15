"""Unit tests for company discovery providers."""

from __future__ import annotations

import httpx
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from agents.scout.providers.csv_import import ManualCSVImportProvider
from agents.scout.providers.web_search import WebSearchProvider
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
async def test_search_based_providers_no_mock_data() -> None:
    """
    Test that search-based providers return empty lists instead of mock data
    when the LLM returns no results.
    """
    mock_llm = MockLLMProvider(return_val=[])
    with patch("agents.scout.providers.base.get_llm_provider", return_value=mock_llm), \
         patch("core.services.search.tavily_provider.TavilySearchProvider.search", return_value=[{"title": "test", "url": "https://test.com", "content": "test"}]):
        provider = WebSearchProvider()
        results = await provider.discover(industry="FinTech", location="San Francisco")
        
        assert len(results) == 0
        assert mock_llm.call_count == 1
        assert provider.metrics.failures == 0
        assert provider.metrics.success_rate == 100.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_web_search_provider_returns_llm_data_with_evidence() -> None:
    """
    Test WebSearchProvider returns the data from the LLM call and attaches the source,
    enforcing that only records with valid evidence are returned.
    """
    mock_llm_response = [
        {
            "name": "AI Startup",
            "industry": "AI",
            "location": "San Francisco",
            "linkedin_url": "https://linkedin.com/company/aistartup",
            "evidence": [
                {
                    "source_url": "https://linkedin.com/company/aistartup",
                    "source_type": "LinkedIn",
                }
            ]
        },
        {
            "name": "Hallucinated Startup",
            "evidence": [] # Should be dropped!
        }
    ]
    
    mock_llm = MockLLMProvider(return_val=mock_llm_response)
    with patch("agents.scout.providers.base.get_llm_provider", return_value=mock_llm), \
         patch("core.services.search.tavily_provider.TavilySearchProvider.search", return_value=[{"title": "test", "url": "https://test.com", "content": "test"}]):
        provider = WebSearchProvider()
        results = await provider.discover(industry="AI", location="San Francisco")
        
        assert len(results) == 1
        assert results[0]["name"] == "Ai Startup"
        assert results[0]["source"] == "web_search"
        assert mock_llm.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_import_provider_success() -> None:
    """
    Test ManualCSVImportProvider correctly parses and maps raw CSV string
    with varying header names.
    """
    csv_data = (
        "Company Name,Company Website,Linkedin URL,Sector,Geography,Careers\n"
        "Acme Corp,https://acme.com,https://linkedin.com/company/acme,SaaS,New York,https://acme.com/jobs\n"
        "Beta LLC,beta.io,https://linkedin.com/company/beta,FinTech,London,\n"
    )

    provider = ManualCSVImportProvider()
    results = await provider.discover(csv_content=csv_data)

    assert len(results) == 2
    
    # Verify Acme Corp mapping
    acme = results[0]
    assert acme["name"] == "Acme Corp"
    assert acme["website"] == "https://acme.com"
    assert acme["linkedin_url"] == "https://linkedin.com/company/acme"
    assert acme["industry"] == "SaaS"
    assert acme["location"] == "New York"
    assert acme["careers_page"] == "https://acme.com/jobs"
    assert acme["source"] == "manual_csv"

    # Verify Beta LLC mapping
    beta = results[1]
    assert beta["name"] == "Beta LLC"
    assert beta["website"] == "beta.io"
    assert beta["linkedin_url"] == "https://linkedin.com/company/beta"
    assert beta["industry"] == "FinTech"
    assert beta["location"] == "London"
    assert "careers_page" not in beta


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_caching() -> None:
    """Test that LLM calls are cached and hit on subsequent calls."""
    mock_llm_response = [
        {
            "name": "Cached Startup",
            "evidence": [{"source_url": "https://cached.com", "source_type": "Website"}]
        }
    ]
    
    mock_llm = MockLLMProvider(return_val=mock_llm_response)
    with patch("agents.scout.providers.base.get_llm_provider", return_value=mock_llm), \
         patch("core.services.search.tavily_provider.TavilySearchProvider.search", return_value=[{"title": "test", "url": "https://test.com", "content": "test"}]):
        provider = WebSearchProvider()
        
        # First call (cache miss)
        results1 = await provider.discover(industry="CacheTech")
        assert len(results1) == 1
        assert mock_llm.call_count == 1
        
        # Second call (cache hit)
        results2 = await provider.discover(industry="CacheTech")
        assert len(results2) == 1
        assert results2[0]["name"] == "Cached Startup"
        assert mock_llm.call_count == 1 # Still 1!


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_retry_logic() -> None:
    """Test that providers retry on HTTP errors using tenacity."""
    # First fails with HTTP error, second succeeds
    mock_llm_response = [
        {
            "name": "Retry Startup",
            "evidence": [{"source_url": "https://retry.com", "source_type": "Website"}]
        }
    ]
    
    # Simulate a timeout or request error
    err = httpx.RequestError("Timeout")
    mock_llm = MockLLMProvider(side_effect=[err, mock_llm_response])
    
    # Need to patch wait to avoid sleeping during tests
    with patch("agents.scout.providers.base.get_llm_provider", return_value=mock_llm), \
         patch("core.services.search.tavily_provider.TavilySearchProvider.search", return_value=[{"title": "test", "url": "https://test.com", "content": "test"}]), \
         patch("tenacity.nap.time.sleep", return_value=None):
        provider = WebSearchProvider()
        
        results = await provider.discover(industry="RetryTech")
        
        assert len(results) == 1
        assert mock_llm.call_count == 2
        assert provider.metrics.retries == 1
