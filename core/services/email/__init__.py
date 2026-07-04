"""Email service providers."""

from core.services.email.base import BaseEmailProvider
from core.services.email.resend_provider import ResendProvider
from core.services.email.smtp_provider import SMTPProvider

def get_email_provider() -> BaseEmailProvider:
    """
    Factory function to get the configured email provider.
    For simplicity, defaults to SMTP if Resend key is missing.
    """
    from core.config import get_settings
    settings = get_settings()
    
    if hasattr(settings, "resend_api_key") and settings.resend_api_key:
        return ResendProvider()
        
    return SMTPProvider()
