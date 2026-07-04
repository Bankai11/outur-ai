"""Base Email Provider interface."""

from abc import ABC, abstractmethod
from typing import Any

class BaseEmailProvider(ABC):
    """Abstract interface for email delivery providers."""
    
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None
    ) -> dict[str, Any]:
        """
        Send an email.
        
        Returns:
            dict containing at least {"success": bool, "message_id": str | None, "error": str | None}
        """
        pass
    
    @abstractmethod
    async def check_replies(self) -> list[dict[str, Any]]:
        """
        Check for replies to sent emails.
        
        Returns:
            list of dicts containing reply details (thread_id, from_email, body, etc.)
        """
        pass
