"""Unit tests for email providers."""

import pytest
from core.services.email.resend_provider import ResendProvider
from core.services.email.smtp_provider import SMTPProvider

@pytest.mark.asyncio
async def test_resend_provider_no_api_key():
    """Test Resend provider fails gracefully without API key."""
    provider = ResendProvider(api_key=None, from_email="test@example.com")
    result = await provider.send_email(
        to_email="recipient@example.com",
        subject="Test",
        body="Hello"
    )
    
    assert result["success"] is False
    assert "RESEND_API_KEY not configured" in result["error"]

@pytest.mark.asyncio
async def test_smtp_provider_no_credentials():
    """Test SMTP provider fails gracefully without credentials."""
    provider = SMTPProvider(smtp_user=None, smtp_pass=None)
    result = await provider.send_email(
        to_email="recipient@example.com",
        subject="Test",
        body="Hello"
    )
    
    assert result["success"] is False
    assert "credentials not configured" in result["error"]
