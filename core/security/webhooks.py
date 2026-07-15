"""Webhook signature verification utilities."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time

logger = logging.getLogger(__name__)

def verify_resend_webhook_signature(
    payload_bytes: bytes,
    headers: dict[str, str],
    secret: str
) -> bool:
    """
    Verify Svix signature used by Resend webhooks.

    Parameters
    ----------
    payload_bytes:
        Raw bytes of request body.
    headers:
        HTTP request headers.
    secret:
        The webhook signing secret (starts with whsec_).

    Returns
    -------
    bool:
        True if signature is valid or secret is empty.
    """
    if not secret:
        # Warn but allow bypass in dev if no secret configured
        logger.warning("No resend_webhook_signing_secret configured. Skipping webhook validation.")
        return True

    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")

    if not svix_id or not svix_timestamp or not svix_signature:
        logger.error("Missing Svix signature headers")
        return False

    # Prevent replay attacks (5 minute threshold)
    try:
        ts = int(svix_timestamp)
        if abs(time.time() - ts) > 300:
            logger.error("Webhook timestamp is expired (replay attack check failed)")
            return False
    except ValueError:
        logger.error("Invalid svix-timestamp value")
        return False

    secret_bytes = secret.encode("utf-8")
    if secret.startswith("whsec_"):
        try:
            clean_secret = secret.replace("whsec_", "")
            secret_bytes = base64.b64decode(clean_secret)
        except Exception:
            secret_bytes = secret.encode("utf-8")

    to_sign = f"{svix_id}.{svix_timestamp}.".encode() + payload_bytes
    computed = hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()
    computed_hex = computed.hex()

    for part in svix_signature.split(" "):
        if "," in part:
            version, signature = part.split(",", 1)
            if version == "v1":
                if hmac.compare_digest(signature, computed_hex):
                    return True
                try:
                    sig_bytes = base64.b64decode(signature)
                    if hmac.compare_digest(sig_bytes, computed):
                        return True
                except Exception as exc:
                    logger.debug(f"Failed decoding signature block: {exc}")

    logger.error("Svix webhook signature verification failed")
    return False
