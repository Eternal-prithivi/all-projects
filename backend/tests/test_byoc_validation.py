"""BYOC validation smoke tests (no live cloud calls)."""

from app.byoc.encryption import encrypt_credential, decrypt_credential


def test_byoc_credential_roundtrip():
  plain = "test-secret-key"
  encrypted = encrypt_credential(plain)
  assert encrypted != plain
  assert decrypt_credential(encrypted) == plain
