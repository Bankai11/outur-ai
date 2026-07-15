"""Pydantic schemas for campaign execution system."""

from pydantic import BaseModel, Field
from typing import Any
from uuid import UUID

class DeliveryResult(BaseModel):
    """Result of an individual delivery attempt."""
    success: bool
    message_id: str | None = None
    error: str | None = None
    is_transient: bool = False


class ProviderConfig(BaseModel):
    """Configuration for a delivery provider."""
    provider_name: str
    rate_limit_per_minute: int = 60
    max_retries: int = 3
    api_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None


class DraftPayload(BaseModel):
    """Payload representing a validated draft to be sent."""
    draft_id: UUID
    campaign_id: UUID
    contact_id: UUID
    contact_email: str
    subject: str
    body: str
