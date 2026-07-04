"""Resend email provider implementation."""

import resend
from typing import Any

from core.services.email.base import BaseEmailProvider
from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)
settings = get_settings()

# We expect RESEND_API_KEY and RESEND_FROM_EMAIL to be in settings/env
if hasattr(settings, "resend_api_key") and settings.resend_api_key:
    resend.api_key = settings.resend_api_key

class ResendProvider(BaseEmailProvider):
    """Email provider using Resend."""
    
    def __init__(self, api_key: str | None = None, from_email: str | None = None):
        self.api_key = api_key or getattr(settings, "resend_api_key", None)
        self.from_email = from_email or getattr(settings, "resend_from_email", "onboarding@resend.dev")
        if self.api_key:
            resend.api_key = self.api_key
            
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None
    ) -> dict[str, Any]:
        """Send an email using Resend API."""
        if not self.api_key:
            log.warning("RESEND_API_KEY not configured. Cannot send email.")
            return {"success": False, "message_id": None, "error": "RESEND_API_KEY not configured"}
            
        try:
            params: dict[str, Any] = {
                "from": self.from_email,
                "to": to_email,
                "subject": subject,
                "text": body,
            }
            if reply_to:
                params["reply_to"] = reply_to
                
            email = resend.Emails.send(params)
            
            return {
                "success": True,
                "message_id": email.get("id"),
                "error": None
            }
        except Exception as e:
            log.error("Failed to send email via Resend", error=str(e), to_email=to_email)
            return {
                "success": False,
                "message_id": None,
                "error": str(e)
            }
            
    async def check_replies(self) -> list[dict[str, Any]]:
        """
        Check for replies. 
        For Resend, replies are typically handled via Inbound Webhooks rather than polling.
        So this returns empty, and the webhook endpoint handles it.
        """
        return []
