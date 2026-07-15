"""Delivery providers for campaign execution."""

import uuid
import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from agents.campaign_execution.models import DeliveryResult, ProviderConfig
from agents.campaign_execution.exceptions import ProviderConfigurationError
from core.utils.circuit_breaker import CircuitBreaker

_circuit_breakers: dict[str, CircuitBreaker] = {}

def get_circuit_breaker(provider_name: str) -> CircuitBreaker:
    """Retrieve or create the CircuitBreaker for a given provider."""
    if provider_name not in _circuit_breakers:
        _circuit_breakers[provider_name] = CircuitBreaker(failure_threshold=3, cooldown_seconds=10.0)
    return _circuit_breakers[provider_name]


class DeliveryProvider(ABC):
    """Abstract base class for all delivery providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._cb = get_circuit_breaker(config.provider_name)

    async def send_email(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        """Send an email, wrapped by a Circuit Breaker."""
        if not self._cb.can_execute():
            return DeliveryResult(
                success=False,
                error="Circuit breaker is OPEN",
                is_transient=True
            )
        try:
            result = await self._send_email_impl(to_email, subject, body)
            if result.success:
                self._cb.record_success()
            else:
                if result.is_transient:
                    self._cb.record_failure()
            return result
        except Exception as e:
            self._cb.record_failure()
            return DeliveryResult(
                success=False,
                error=f"Provider exception: {e}",
                is_transient=True
            )

    @abstractmethod
    async def _send_email_impl(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        """Specific provider implementation to send an email."""
        pass

    @abstractmethod
    async def validate_configuration(self) -> bool:
        """Validate that the provider is correctly configured."""
        pass


class MockProvider(DeliveryProvider):
    """A mock provider that simulates email delivery for testing."""
    
    async def _send_email_impl(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        # Simulate network latency
        await asyncio.sleep(0.5)
        
        # In a real mock, you could inject failures based on to_email for testing
        if "fail@example.com" in to_email:
            return DeliveryResult(
                success=False,
                error="Simulated permanent failure",
                is_transient=False
            )
        if "timeout@example.com" in to_email:
            return DeliveryResult(
                success=False,
                error="Simulated transient timeout",
                is_transient=True
            )
            
        return DeliveryResult(
            success=True,
            message_id=f"mock-{uuid.uuid4()}"
        )

    async def validate_configuration(self) -> bool:
        return True


class SMTPProvider(DeliveryProvider):
    """Traditional SMTP delivery provider."""
    
    async def _send_email_impl(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        # TODO: Implement real aiosmtplib logic here
        # For now, act as a stub until aiosmtplib is added to requirements
        return DeliveryResult(success=True, message_id=f"smtp-{uuid.uuid4()}")

    async def validate_configuration(self) -> bool:
        if not self.config.smtp_host or not self.config.smtp_port:
            raise ProviderConfigurationError("SMTP host and port are required")
        return True


class GmailProvider(DeliveryProvider):
    """OAuth-based Gmail API delivery provider."""
    
    async def _send_email_impl(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        # TODO: Implement google-api-python-client logic
        return DeliveryResult(success=True, message_id=f"gmail-{uuid.uuid4()}")

    async def validate_configuration(self) -> bool:
        if not self.config.api_key:
            raise ProviderConfigurationError("Gmail OAuth token/api_key is required")
        return True


class SendGridProvider(DeliveryProvider):
    """SendGrid API delivery provider."""
    
    async def _send_email_impl(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        # TODO: Implement sendgrid SDK logic
        return DeliveryResult(success=True, message_id=f"sg-{uuid.uuid4()}")

    async def validate_configuration(self) -> bool:
        if not self.config.api_key:
            raise ProviderConfigurationError("SendGrid API key is required")
        return True


class MicrosoftGraphProvider(DeliveryProvider):
    """Microsoft Graph API delivery provider for O365."""
    
    async def _send_email_impl(self, to_email: str, subject: str, body: str) -> DeliveryResult:
        # TODO: Implement msgraph-sdk-python logic
        return DeliveryResult(success=True, message_id=f"msgraph-{uuid.uuid4()}")

    async def validate_configuration(self) -> bool:
        if not self.config.api_key:
            raise ProviderConfigurationError("Microsoft Graph credentials required")
        return True

