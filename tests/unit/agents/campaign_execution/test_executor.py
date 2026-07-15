import pytest
from uuid import uuid4

from agents.campaign_execution.models import DraftPayload
from agents.campaign_execution.validation import DeliveryValidator
from agents.campaign_execution.exceptions import ValidationError
from agents.campaign_execution.retry import calculate_backoff

def test_delivery_validation_success():
    draft = DraftPayload(
        draft_id=uuid4(),
        campaign_id=uuid4(),
        contact_id=uuid4(),
        contact_email="test@example.com",
        subject="Test Subject",
        body="Hello World"
    )
    # Should not raise
    DeliveryValidator.validate_draft(draft)

def test_delivery_validation_invalid_email():
    draft = DraftPayload(
        draft_id=uuid4(),
        campaign_id=uuid4(),
        contact_id=uuid4(),
        contact_email="not-an-email",
        subject="Test Subject",
        body="Hello World"
    )
    with pytest.raises(ValidationError, match="Invalid email format"):
        DeliveryValidator.validate_draft(draft)

def test_calculate_backoff():
    # Base delay = 60s. Attempt 0 => 60s
    delay_0 = calculate_backoff(attempt=0, base_delay=60)
    assert 48 <= delay_0 <= 72 # 60 +/- 20% jitter
    
    # Attempt 1 => 120s
    delay_1 = calculate_backoff(attempt=1, base_delay=60)
    assert 96 <= delay_1 <= 144
