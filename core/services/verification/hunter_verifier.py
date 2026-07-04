import os
import httpx
from typing import Dict, Any, Tuple
from core.services.verification.base import VerificationProvider
from core.logger import get_logger

logger = get_logger(__name__)

class HunterVerificationProvider(VerificationProvider):
    """
    Real email verification using Hunter.io's Email Verifier API.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("HUNTER_API_KEY")
        self.base_url = "https://api.hunter.io/v2/email-verifier"

    async def verify_email(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        if not self.api_key:
            logger.warning("Hunter API key not found. Failing open for mock/dev environment.")
            return True, {
                "status": "valid",
                "score": 100,
                "mx_valid": True,
                "reason": "mocked (no API key)"
            }
            
        params = {
            "email": email,
            "api_key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json().get("data", {})
                
                status = data.get("status")
                score = data.get("score", 0)
                
                smtp_check = data.get("smtp_check")
                mx_records = data.get("mx_records")
                
                mx_valid = mx_records is True or (smtp_check is True)
                
                # Strict rules for production safety (Phase 4 requirement)
                # Only accept "valid" status and >= 95 confidence
                is_valid = status == "valid" and score >= 95 and mx_valid
                
                return is_valid, {
                    "status": status,
                    "score": score,
                    "mx_valid": mx_valid,
                    "reason": "Hunter API verification"
                }
                
        except Exception as e:
            logger.error(f"Hunter verification failed for {email}: {e}")
            # Fail closed on API error to prevent sending to bad emails
            return False, {
                "status": "error",
                "score": 0,
                "mx_valid": False,
                "reason": str(e)
            }
