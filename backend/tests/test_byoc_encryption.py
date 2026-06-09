"""BYOC credential encryption — field-level AES-GCM and incremental merge."""

from app.byoc.encryption import (
    ENCRYPTED_V1_PREFIX,
    decrypt_credential,
    decrypt_credentials_dict,
    encrypt_credential,
    encrypt_credentials_dict,
    is_encrypted_credential,
    merge_and_encrypt_credentials,
)


def test_encrypt_decrypt_roundtrip():
    plain = "AKIAIOSFODNN7EXAMPLE"
    enc = encrypt_credential(plain)
    assert enc.startswith(ENCRYPTED_V1_PREFIX)
    assert is_encrypted_credential(enc)
    assert decrypt_credential(enc) == plain


def test_encrypt_is_idempotent():
    plain = "super-secret-key"
    once = encrypt_credential(plain)
    twice = encrypt_credential(once)
    assert once == twice
    assert decrypt_credential(twice) == plain


def test_each_field_gets_unique_ciphertext():
    a = encrypt_credential("same-value")
    b = encrypt_credential("same-value")
    assert a != b
    assert decrypt_credential(a) == decrypt_credential(b)


def test_merge_keeps_existing_when_incoming_empty():
    existing = encrypt_credentials_dict(
        {"account_key": "key-one", "account_name": "acct"}
    )
    merged = merge_and_encrypt_credentials(
        existing,
        {"account_key": "", "client_secret": "new-secret"},
    )
    assert merged["account_name"] == existing["account_name"]
    assert decrypt_credential(merged["account_key"]) == "key-one"
    assert decrypt_credential(merged["client_secret"]) == "new-secret"


def test_decrypt_credentials_dict_skips_plaintext():
    enc = encrypt_credentials_dict({"access_key_id": "AKIA123"})
    enc["region"] = "ap-south-1"
    dec = decrypt_credentials_dict(enc)
    assert dec["access_key_id"] == "AKIA123"
    assert dec["region"] == "ap-south-1"


def test_legacy_blob_without_prefix_still_decrypts():
    plain = "legacy-secret"
    # Simulate pre-v1 storage: base64 only
    from app.byoc.encryption import _get_master_key, _NONCE_LENGTH
    import os
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_master_key()
    nonce = os.urandom(_NONCE_LENGTH)
    ciphertext = AESGCM(key).encrypt(nonce, plain.encode("utf-8"), None)
    legacy = base64.b64encode(nonce + ciphertext).decode("utf-8")
    assert is_encrypted_credential(legacy)
    assert decrypt_credential(legacy) == plain
