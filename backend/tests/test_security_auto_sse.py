"""Tests for auto SSE-S3 path on sensitive secure uploads."""

from unittest.mock import MagicMock, patch

import pytest

from app.security.sensitive_file_detector import scan_file_content


def test_scan_detects_api_key():
    result = scan_file_content(b"api_key=secretvalue123", "secrets.txt")
    assert result.is_sensitive
    assert "credential_keywords" in result.reasons


@patch("app.security.routes_security.put_secure_object_dual")
def test_persist_sse_secure_file_sets_metadata(mock_put):
    from app.security.routes_security import _persist_sse_secure_file

    files_db = MagicMock()
    storage = MagicMock()
    storage.object_key.return_value = "alice/test.txt"
    storage.primary_bucket = "secure-b"
    storage.is_byoc = False
    result = _persist_sse_secure_file(
        files_db,
        filename="test.txt",
        owner_username="alice",
        file_content=b"api_key=xyz",
        is_sensitive=True,
        storage=storage,
        scan_reasons=["credential_keywords"],
    )
    assert result["status"] == "auto_encrypted_sse"
    assert result["encryption_method"] == "server-side"
    mock_put.assert_called_once()
    files_db.update_one.assert_called_once()
