"""Archive password helpers."""

import pytest

from app.auth.auth_utils import get_password_hash, verify_password
from app.security.archive_password import (
    ArchivePasswordError,
    archive_password_required,
    hash_archive_password,
    require_archived_file_access,
    validate_archive_password,
    verify_archived_file_access,
)


def test_validate_archive_password_min_length():
    with pytest.raises(ArchivePasswordError):
        validate_archive_password("abc")
    validate_archive_password("secret123")


def test_hash_and_verify_archive_password():
    hashed = hash_archive_password("my-archive-pass")
    doc = {"vault_status": "archived", "archive_password_hash": hashed}
    assert verify_archived_file_access(doc, "my-archive-pass")
    assert not verify_archived_file_access(doc, "wrong")


def test_legacy_archived_without_hash_allows_access():
    doc = {"vault_status": "archived"}
    assert verify_archived_file_access(doc, None)
    assert archive_password_required(doc) is False


def test_active_file_does_not_require_password():
    doc = {"vault_status": "active", "archive_password_hash": get_password_hash("x")}
    assert verify_archived_file_access(doc, None)
    require_archived_file_access(doc, None)
