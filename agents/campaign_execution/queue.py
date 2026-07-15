"""ARQ tasks for asynchronous campaign execution."""

import time
import logging
from uuid import UUID

from core.database.engine import async_session_factory
from core.models.execution import CampaignDelivery, DeliveryAttempt
from agents.campaign_execution.models import DraftPayload, ProviderConfig
from agents.campaign_execution.providers import MockProvider, DeliveryProvider
from agents.campaign_execution.validation import DeliveryValidator
from agents.campaign_execution.rate_limit import RateLimiter
from agents.campaign_execution.retry import calculate_backoff
from agents.campaign_execution.exceptions import ValidationError

log = logging.getLogger(__name__)

def get_provider(config: ProviderConfig) -> DeliveryProvider:
    """Factory to instantiate the appropriate provider."""
    # For now, we only implement the MockProvider fully.
    # In a real system, you would switch on config.provider_name.
    return MockProvider(config)

async def send_email_job(ctx: dict, delivery_id: str, draft_dict: dict, provider_dict: dict, attempt: int = 0) -> None:
    """
    ARQ job to execute the delivery of a single email draft.
    """
    redis = ctx["redis"]
    draft_payload = DraftPayload(**draft_dict)
    provider_config = ProviderConfig(**provider_dict)
    
    delivery_uuid = UUID(delivery_id)
    
    # Initialize components
    provider = get_provider(provider_config)
    rate_limiter = RateLimiter(redis)
    
    async with async_session_factory() as session:
        # Pre-flight validation
        start_time = time.time()
        try:
            DeliveryValidator.validate_draft(draft_payload)
        except ValidationError as e:
            log.error(f"Validation failed for draft {draft_payload.draft_id}: {e}")
            # Log attempt and update delivery
            db_attempt = DeliveryAttempt(
                delivery_id=delivery_uuid,
                attempt_number=attempt,
                status="validation_failed",
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
            session.add(db_attempt)
            
            delivery = await session.get(CampaignDelivery, delivery_uuid)
            if delivery:
                delivery.status = "failed"
                delivery.error_message = str(e)
            await session.commit()
            return

        # Respect Rate Limits
        await rate_limiter.wait_if_needed(provider_config.provider_name, provider_config.rate_limit_per_minute)
        
        # Execute Delivery
        start_time = time.time()
        result = await provider.send_email(
            to_email=draft_payload.contact_email,
            subject=draft_payload.subject,
            body=draft_payload.body
        )
        latency_ms = (time.time() - start_time) * 1000
        
        # Record Attempt
        db_attempt = DeliveryAttempt(
            delivery_id=delivery_uuid,
            attempt_number=attempt,
            status="success" if result.success else "failed",
            error_message=result.error,
            latency_ms=latency_ms
        )
        session.add(db_attempt)
        
        # Update Delivery State
        delivery = await session.get(CampaignDelivery, delivery_uuid)
        if delivery:
            if result.success:
                delivery.status = "delivered"
                delivery.provider_message_id = result.message_id
            else:
                if result.is_transient and attempt < provider_config.max_retries:
                    # Enqueue retry
                    backoff = calculate_backoff(attempt)
                    delivery.status = "retrying"
                    delivery.retry_count = attempt + 1
                    # Enqueue next attempt
                    await ctx["redis"].enqueue_job(
                        "send_email_job",
                        delivery_id,
                        draft_dict,
                        provider_dict,
                        attempt + 1,
                        _defer_by=backoff
                    )
                else:
                    delivery.status = "failed"
                    delivery.error_message = result.error
        
        await session.commit()
