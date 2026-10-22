"""AEGIS Authenticated Encryption for Endpoint Secrets at Rest.

Implements PBKDF2-HMAC-SHA256 authenticated keystream encryption using
the Python standard library (no external C-extensions required).
Protects admin secrets, webhook tokens, and HMAC signing keys.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path
from typing import Optional

KEY_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / ".master.key"


def _get_master_key() -> bytes:
    """Retrieve or generate the persistent system master key."""
    env_key = os.environ.get("AEGIS_MASTER_KEY")
    if env_key and env_key.strip():
        return env_key.strip().encode("utf-8")

    # If file exists, read it
    KEY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_FILE_PATH.exists():
        try:
            with open(KEY_FILE_PATH, "rb") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        except Exception:
            pass

    # Generate new random 32-byte key
    new_key = secrets.token_bytes(32)
    try:
        with open(KEY_FILE_PATH, "wb") as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key


def _derive_keys(master_key: bytes, salt: bytes) -> tuple[bytes, bytes]:
    """Derive 32-byte encryption key and 32-byte MAC key using PBKDF2-HMAC-SHA256."""
    derived = hashlib.pbkdf2_hmac("sha256", master_key, salt, iterations=50_000, dklen=64)
    return derived[:32], derived[32:]


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate CTR-mode pseudorandom keystream using HMAC-SHA256."""
    blocks: list[bytes] = []
    block_counter = 0
    produced = 0
    while produced < length:
        counter_bytes = block_counter.to_bytes(4, byteorder="big")
        block = hmac.new(enc_key, nonce + counter_bytes, hashlib.sha256).digest()
        blocks.append(block)
        produced += len(block)
        block_counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string into an authenticated cipher payload.

    Format: enc:v1:<base64(salt(16) + nonce(16) + ciphertext(N) + hmac(32))>
    """
    if not plaintext:
        return ""

    master_key = _get_master_key()
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)

    enc_key, mac_key = _derive_keys(master_key, salt)
    plain_bytes = plaintext.encode("utf-8")

    keystream = _keystream(enc_key, nonce, len(plain_bytes))
    ciphertext = bytes(a ^ b for a, b in zip(plain_bytes, keystream))

    # Authenticate salt + nonce + ciphertext
    tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()

    payload = salt + nonce + ciphertext + tag
    encoded = base64.urlsafe_b64encode(payload).decode("ascii")
    return f"enc:v1:{encoded}"


def decrypt_secret(encrypted_str: str) -> Optional[str]:
    """Verify and decrypt an authenticated cipher payload.

    Returns:
        The decrypted plaintext string, or None if invalid/tampered.
    """
    if not encrypted_str or not encrypted_str.startswith("enc:v1:"):
        return None

    raw_encoded = encrypted_str[len("enc:v1:"):]
    try:
        payload = base64.urlsafe_b64decode(raw_encoded.encode("ascii"))
    except Exception:
        return None

    if len(payload) < 64:  # salt(16) + nonce(16) + tag(32) minimum
        return None

    salt = payload[:16]
    nonce = payload[16:32]
    ciphertext = payload[32:-32]
    tag = payload[-32:]

    master_key = _get_master_key()
    enc_key, mac_key = _derive_keys(master_key, salt)

    # Verify MAC in constant time
    expected_tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        return None

    keystream = _keystream(enc_key, nonce, len(ciphertext))
    plain_bytes = bytes(a ^ b for a, b in zip(ciphertext, keystream))
    try:
        return plain_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
