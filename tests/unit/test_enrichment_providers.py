"""Unit tests for enrichment providers."""

from __future__ import annotations

import pytest

from agents.researcher.enrichment_providers.careers_analyser import CareersAnalyserProvider
from agents.researcher.enrichment_providers.news import NewsEnrichmentProvider
from agents.researcher.enrichment_providers.social import SocialEnrichmentProvider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_news_enrichment_provider() -> None:
    provider = NewsEnrichmentProvider()
    res = await provider.enrich("Plaid", "plaid.com")
    assert res["provider_name"] == "news"
    assert "news_headlines" in res["raw_evidence"]
    assert len(res["insights"]) > 0
    assert any("Plaid" in insight["text"] for insight in res["insights"])
    assert res["insights"][0]["source_url"].startswith("http")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_social_enrichment_provider() -> None:
    provider = SocialEnrichmentProvider()
    res = await provider.enrich("Stripe", "stripe.com")
    assert res["provider_name"] == "social"
    assert "recent_posts" in res["raw_evidence"]
    assert "social_metrics" in res["raw_evidence"]
    assert len(res["insights"]) > 0
    assert res["insights"][0]["source_url"].startswith("http")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_careers_analyser_enrichment_provider() -> None:
    provider = CareersAnalyserProvider()
    res = await provider.enrich("Datadog", "datadoghq.com")
    assert res["provider_name"] == "careers_analyser"
    assert "open_roles" in res["raw_evidence"]
    assert "technologies_found" in res["raw_evidence"]
    assert len(res["insights"]) > 0
    assert res["insights"][0]["source_url"].startswith("http")
