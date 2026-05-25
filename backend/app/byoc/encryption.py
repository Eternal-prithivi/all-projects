"""
BYOC (Bring Your Own Cloud) Credential Encryption Service.

Encrypts user-provided cloud credentials at rest using AES-256-GCM.
Keys are decrypted only in memory when making API calls.
"""

import os
import base64
import json
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Master encryption key — derived from the app's SECRET_KEY
# In production, this should be a separate key stored in a KMS (e.g., AWS KMS, HashiCorp Vault)
_master_key = None


def _get_master_key() -> bytes:
    """Derive a 256-bit encryption key from the app's SECRET_KEY."""
    global _master_key
    if _master_key is None:
        from app.utils.config import settings
        # SHA-256 hash of SECRET_KEY gives us a consistent 32-byte key
        _master_key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    return _master_key


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential string using AES-256-GCM.
    
    Returns:
        Base64-encoded string containing nonce + ciphertext.
        Format: base64(nonce || ciphertext || tag)
    """
    if not plaintext:
        return ""
    
    key = _get_master_key()
    aesgcm = AESGCM(key)
    
    # Generate a random 96-bit nonce (12 bytes)
    nonce = os.urandom(12)
    
    # Encrypt
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    
    # Combine nonce + ciphertext and base64 encode
    encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
    return encrypted


def decrypt_credential(encrypted: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted credential.
    
    Args:
        encrypted: Base64-encoded string from encrypt_credential()
    
    Returns:
        Original plaintext string.
    """
    if not encrypted:
        return ""
    
    key = _get_master_key()
    aesgcm = AESGCM(key)
    
    # Decode base64
    raw = base64.b64decode(encrypted)
    
    # First 12 bytes are the nonce, rest is ciphertext + tag
    nonce = raw[:12]
    ciphertext = raw[12:]
    
    # Decrypt
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


def encrypt_credentials_dict(credentials: dict) -> dict:
    """Encrypt all values in a credentials dictionary."""
    encrypted = {}
    for key, value in credentials.items():
        if value and isinstance(value, str):
            encrypted[key] = encrypt_credential(value)
        else:
            encrypted[key] = value
    return encrypted


def decrypt_credentials_dict(encrypted: dict) -> dict:
    """Decrypt all values in an encrypted credentials dictionary."""
    decrypted = {}
    for key, value in encrypted.items():
        if value and isinstance(value, str) and len(value) > 30:
            # Only try to decrypt values that look like encrypted data (long base64 strings)
            try:
                decrypted[key] = decrypt_credential(value)
            except Exception:
                decrypted[key] = value  # Not encrypted, keep as-is
        else:
            decrypted[key] = value
    return decrypted
