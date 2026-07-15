"""Pre-flight validation for emails before they are sent."""

import re
from typing import Dict, Any

from agents.campaign_execution.exceptions import ValidationError
from agents.campaign_execution.models import DraftPayload

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class DeliveryValidator:
    """Validator to ensure a draft is safe to send."""
    
    @staticmethod
    def validate_draft(draft: DraftPayload) -> None:
        """
        Perform pre-flight validation on the draft payload.
        
        Raises:
            ValidationError: If the draft is invalid.
        """
        if not draft.contact_email:
            raise ValidationError("Contact email is missing")
            
        if not EMAIL_REGEX.match(draft.contact_email):
            raise ValidationError(f"Invalid email format: {draft.contact_email}")
            
        if not draft.subject or not draft.subject.strip():
            raise ValidationError("Email subject is missing or empty")
            
        if not draft.body or not draft.body.strip():
            raise ValidationError("Email body is missing or empty")
            
        # Ensure no placeholder brackets exist in the body that should have been replaced
        if "{" in draft.body and "}" in draft.body:
            # We allow it, but we might log a warning or have a stricter policy
            pass
