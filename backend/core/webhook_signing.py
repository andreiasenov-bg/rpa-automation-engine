"""Webhook HMAC signature generation and verification.

All outbound webhooks are signed with HMAC-SHA256 to allow receivers
to verify the payload authenticity.

Headers added to outbound webhooks:
  X-RPA-Signature: sha256=<hex_digest>
  X-RPA-Timestamp: <unix_timestamp>
  X-RPA-Delivery: <unique_delivery_id>

Verification:
  1. Check timestamp is within tolerance (default: 5 minutes)
  2. Compute HMAC-SHA256 over: f"{timestamp}.{body}"
  3. Compare computed signature with X-RPA-Signature using constant-time comparison

Usage:
    # Signing (outbound)
    headers = sign_webhook_payload(body_bytes, secret)

    # Verification (inbound)
    is_valid = verify_webhook_signature(body_bytes, secret, signature, timestamp)
"""

import hashlib
import hmac
import time
from typing import Optional
from uuid import uuid4


DEFAULT_TOLERANCE_SECONDS = 300  # 5 minutes


def sign_webhook_payload(
    payload: bytes,
    secret: str,
    timestamp: Optional[int] = None,
    delivery_id: Optional[str] = None,
) -> dict[str, str]:
    """Sign a webhook payload and return headers to include in the request.

    Args:
        payload: Raw request body bytes
        secret: Webhook signing secret (shared with receiver)
        timestamp: Unix timestamp (defaults to now)
        delivery_id: Unique delivery ID (defaults to UUID)

    Returns:
        Dict of headers to add to the webhook request
    """
    ts = timestamp or int(time.time())
    delivery = delivery_id or str(uuid4())

    # Sign: HMAC-SHA256 over "{timestamp}.{payload}"
    sign_input = f"{ts}.".encode() + payload
    signature = hmac.new(
        secret.encode(),
        sign_input,
        hashlib.sha256,
    ).hexdigest()

    return {
        "X-RPA-Signature": f"sha256={signature}",
        "X-RPA-Timestamp": str(ts),
        "X-RPA-Delivery": delivery,
        "Content-Type": "application/json",
    }


def verify_webhook_signature(
    payload: bytes,
    secret: str,
    signature_header: str,
    timestamp_header: str,
    tolerance: int = DEFAULT_TOLERANCE_SECONDS,
) -> bool:
    """Verify a webhook signature.

    Args:
        payload: Raw request body bytes
        secret: Webhook signing secret
        signature_header: Value of X-RPA-Signature header
        timestamp_header: Value of X-RPA-Timestamp header
        tolerance: Maximum age of the webhook in seconds

    Returns:
        True if signature is valid and timestamp is within tolerance
    """
    # Parse timestamp
    try:
        ts = int(timestamp_header)
    except (ValueError, TypeError):
        return False

    # Check timestamp tolerance
    now = int(time.time())
    if abs(now - ts) > tolerance:
        return False

    # Parse signature
    if not signature_header.startswith("sha256="):
        return False
    expected_sig = signature_header[7:]

    # Compute signature
    sign_input = f"{ts}.".encode() + payload
    computed_sig = hmac.new(
        secret.encode(),
        sign_input,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(computed_sig, expected_sig)


def generate_webhook_secret() -> str:
    """Generate a cryptographically secure webhook signing secret."""
    import secrets
    return f"whsec_{secrets.token_urlsafe(32)}"
