"""
BYOC (Bring Your Own Cloud) Credential Encryption Service.

Each credential field is encrypted independently at rest using AES-256-GCM with a
unique random nonce per field. Values are never stored in plaintext in MongoDB.
Decryption happens only in memory when making cloud API calls.

Format (v1): zenith:enc:v1:<base64(nonce_12_bytes || ciphertext || tag)>
Legacy (pre-v1): <base64(nonce_12_bytes || ciphertext || tag)> without prefix
"""

import os
import base64
import hashlib
import re
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

ENCRYPTED_V1_PREFIX = "zenith:enc:v1:"
_NONCE_LENGTH = 12
# Minimum plausible ciphertext payload after base64 decode (nonce + tag + 1 byte)
_MIN_ENCRYPTED_RAW_LEN = _NONCE_LENGTH + 16 + 1
_BASE64_LIKE = re.compile(r"^[A-Za-z0-9+/]+=*$")

_master_key = None


def _get_master_key() -> bytes:
    """Derive a 256-bit encryption key from the app's SECRET_KEY."""
    global _master_key
    if _master_key is None:
        from app.utils.config import settings

        _master_key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return _master_key


def _strip_prefix(encrypted: str) -> str:
    if encrypted.startswith(ENCRYPTED_V1_PREFIX):
        return encrypted[len(ENCRYPTED_V1_PREFIX) :]
    return encrypted


def is_encrypted_credential(value: Any) -> bool:
    """Return True if value looks like an encrypted credential blob."""
    if not value or not isinstance(value, str):
        return False
    if value.startswith(ENCRYPTED_V1_PREFIX):
        return True
    # Legacy blobs: long base64, not JSON service-account paste
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return False
    if len(stripped) < 32 or not _BASE64_LIKE.match(stripped):
        return False
    try:
        raw = base64.b64decode(stripped, validate=True)
    except Exception:
        return False
    return len(raw) >= _MIN_ENCRYPTED_RAW_LEN


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential string using AES-256-GCM.

    Idempotent: already-encrypted values are returned unchanged (no double encryption).
    """
    if not plaintext:
        return ""
    if is_encrypted_credential(plaintext):
        return plaintext

    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(_NONCE_LENGTH)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = base64.b64encode(nonce + ciphertext).decode("utf-8")
    return f"{ENCRYPTED_V1_PREFIX}{payload}"


def decrypt_credential(encrypted: str) -> str:
    """Decrypt an AES-256-GCM encrypted credential (v1 or legacy format)."""
    if not encrypted:
        return ""

    key = _get_master_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(_strip_prefix(encrypted))
    nonce = raw[:_NONCE_LENGTH]
    ciphertext = raw[_NONCE_LENGTH:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def encrypt_credentials_dict(credentials: dict) -> dict:
    """Encrypt plaintext string values; skip empty and already-encrypted values."""
    encrypted: Dict[str, Any] = {}
    for key, value in credentials.items():
        if value is None:
            continue
        if isinstance(value, str):
            if not value.strip():
                continue
            encrypted[key] = encrypt_credential(value)
        else:
            encrypted[key] = value
    return encrypted


def decrypt_credentials_dict(encrypted: dict) -> dict:
    """Decrypt credential fields that are encrypted; pass through others."""
    decrypted: Dict[str, Any] = {}
    for key, value in (encrypted or {}).items():
        if value and isinstance(value, str) and is_encrypted_credential(value):
            try:
                decrypted[key] = decrypt_credential(value)
            except Exception:
                logger.warning("BYOC decrypt failed for field %s — keeping stored value", key)
                decrypted[key] = value
        else:
            decrypted[key] = value
    return decrypted


def merge_and_encrypt_credentials(
    existing_encrypted: Optional[dict],
    incoming_plain: dict,
) -> dict:
    """
    Incrementally update stored credentials.

    - Non-empty incoming plaintext fields are encrypted and replace that key.
    - Omitted or empty incoming fields keep the existing encrypted value.
    - Prevents double-encryption when a value is already stored encrypted.
    """
    result: Dict[str, Any] = dict(existing_encrypted or {})
    for key, value in (incoming_plain or {}).items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, str) and is_encrypted_credential(value):
            result[key] = value
        else:
            result[key] = encrypt_credential(str(value).strip())
    return result
