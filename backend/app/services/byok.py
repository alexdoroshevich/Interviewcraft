"""BYOK (Bring Your Own Key) — encrypt/decrypt user-supplied API keys.

Keys are encrypted at rest using Fernet symmetric encryption.
The encryption key is derived from the application's secret_key via SHA-256.
Keys are NEVER logged; only provider names and masked previews are safe to log.

Supported providers: anthropic, openai, deepgram, elevenlabs
"""

from __future__ import annotations

import base64
import hashlib

import structlog
from cryptography.fernet import Fernet, InvalidToken

logger = structlog.get_logger(__name__)

# Provider names accepted in byok_keys dict
SUPPORTED_PROVIDERS = frozenset({"anthropic", "openai", "deepgram", "elevenlabs"})


def _make_fernet(secret_key: str) -> Fernet:
    """Derive a Fernet instance from the app's secret key (SHA-256 → 32 bytes)."""
    key_bytes = hashlib.sha256(secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_api_key(raw_key: str, secret_key: str) -> str:
    """Encrypt a plaintext API key for storage in the database.

    Args:
        raw_key: The plaintext API key (e.g. "sk-ant-api03-...").
        secret_key: The application secret (from settings.secret_key).

    Returns:
        Base64-encoded Fernet token suitable for JSONB storage.
    """
    fernet = _make_fernet(secret_key)
    token: bytes = fernet.encrypt(raw_key.encode())
    return token.decode()


def decrypt_api_key(encrypted: str, secret_key: str) -> str | None:
    """Decrypt a stored API key. Returns None on failure (don't raise).

    Args:
        encrypted: The stored Fernet token string.
        secret_key: The application secret (from settings.secret_key).

    Returns:
        Plaintext API key, or None if decryption fails.
    """
    try:
        fernet = _make_fernet(secret_key)
        return fernet.decrypt(encrypted.encode()).decode()
    except (InvalidToken, Exception) as exc:
        logger.warning("byok.decrypt_failed", error=type(exc).__name__)
        return None


def mask_key(raw_key: str) -> str:
    """Return a safe display string showing only the last 4 characters.

    Example: "sk-ant-api03-abc123xyz" → "sk-ant-api...xyz"
    Never returns the full key.
    """
    if len(raw_key) <= 8:
        return "****"
    prefix = raw_key[:7]
    suffix = raw_key[-4:]
    return f"{prefix}...{suffix}"


def decrypt_byok_keys(
    byok_keys: dict[str, str] | None,
    secret_key: str,
) -> dict[str, str]:
    """Decrypt all provider keys stored in user.byok_keys.

    Args:
        byok_keys: The JSONB dict from user.byok_keys (encrypted values).
        secret_key: The application secret.

    Returns:
        Dict mapping provider name → plaintext key (only successfully decrypted keys).
    """
    if not byok_keys:
        return {}

    result: dict[str, str] = {}
    for provider, encrypted_value in byok_keys.items():
        if provider not in SUPPORTED_PROVIDERS:
            continue
        plaintext = decrypt_api_key(encrypted_value, secret_key)
        if plaintext:
            result[provider] = plaintext
    return result
