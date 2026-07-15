"""Campaign Execution Custom Exceptions."""

class CampaignExecutionError(Exception):
    """Base exception for campaign execution errors."""
    pass


class ValidationError(CampaignExecutionError):
    """Raised when an outreach draft fails pre-flight validation."""
    pass


class ProviderConfigurationError(CampaignExecutionError):
    """Raised when a delivery provider is improperly configured."""
    pass


class RateLimitExceededError(CampaignExecutionError):
    """Raised when a provider's rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class TransientDeliveryError(CampaignExecutionError):
    """Raised when a delivery fails but is expected to succeed upon retry."""
    pass


class PermanentDeliveryError(CampaignExecutionError):
    """Raised when a delivery fails and should not be retried."""
    pass
