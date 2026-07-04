from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class VerificationProvider(ABC):
    """
    Abstract base class for email verification providers.
    """
    
    @abstractmethod
    async def verify_email(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify an email address.
        
        Args:
            email: The email address to verify.
            
        Returns:
            Tuple containing:
            - is_valid (bool): True if the email is safe to send to (strict criteria).
            - details (dict): Detailed verification results.
              Expected keys:
              - status (str): "valid", "invalid", "accept_all", "unknown"
              - mx_valid (bool)
              - score (int): Deliverability confidence score (0-100)
        """
        pass
