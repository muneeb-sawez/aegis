"""GitHub Webhook HMAC Signature Verification.

Verifies X-Hub-Signature-256 header using timing-safe hmac.compare_digest.
Rejects forged, tampered, or unsigned webhook deliveries.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from backend.config import settings


def compute_github_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute GitHub's standard X-Hub-Signature-256 string for a payload."""
    sig_hex = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig_hex}"


def verify_github_signature(
    payload_bytes: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None,
) -> bool:
    """Verify that the X-Hub-Signature-256 header matches payload HMAC.

    Uses hmac.compare_digest to prevent timing attacks.
    Returns True if valid, False if missing, malformed, or mismatch.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    signing_secret = secret or settings.GITHUB_WEBHOOK_SECRET
    if not signing_secret:
        return False

    expected_sig = compute_github_signature(payload_bytes, signing_secret)
    return hmac.compare_digest(signature_header.strip(), expected_sig)
