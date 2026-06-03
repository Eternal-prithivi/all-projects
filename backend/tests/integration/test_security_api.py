"""Security vault API integration tests — auth and 2FA guards."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_list_secure_unauthorized(client):
    response = client.get("/api/security/list-secure")
    assert response.status_code == 401


def test_list_secure_requires_2fa_when_enabled(client, auth_headers, db):
    headers, user = auth_headers(two_fa_enabled=True, two_fa_verified=False)
    response = client.get("/api/security/list-secure", headers=headers)
    assert response.status_code == 403
    assert "2FA" in response.json()["detail"]


def test_list_secure_ok_without_2fa(client, auth_headers):
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.get("/api/security/list-secure", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch("app.security.routes_security.put_secure_vault_object")
@patch("app.security.routes_security.resolve_secure_storage")
def test_upload_client_encrypted_smoke(mock_storage, mock_put, client, auth_headers):
    mock_storage.return_value = SimpleNamespace(
        primary_bucket="test-secure-bucket",
        is_byoc=False,
        object_key=lambda username, filename: f"{username}/{filename}",
    )
    headers, _user = auth_headers(two_fa_enabled=False)
    ciphertext = b"x" * 40

    response = client.post(
        "/api/security/upload-client-encrypted",
        headers=headers,
        files={"file": ("cipher.bin", ciphertext, "application/octet-stream")},
        data={"original_filename": "secret-doc.txt", "is_sensitive": "false"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["client_side_encrypted"] is True
    assert body["filename"] == "secret-doc.txt"
    mock_put.assert_called_once()


@patch("app.security.routes_security._sync_secure_objects")
def test_sync_secure_gcp_route(mock_sync, client, auth_headers):
    from app.security.routes_security import SecureSyncResponse

    mock_sync.return_value = SecureSyncResponse(
        inserted=1,
        already_present=0,
        removed=0,
        skipped_non_user_prefix=0,
        total_objects_seen=1,
        bucket_name="gcp-secure-bucket",
        scanned_prefix="secure/alice/",
    )
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.post("/api/security/sync/GCP", headers=headers)
    assert response.status_code == 200, response.text
    mock_sync.assert_called_once()


@patch("app.security.routes_security.resolve_secure_storage")
@patch("app.security.routes_security.put_secure_vault_object")
@patch("app.security.routes_security.scan_file_content")
def test_upload_secure_with_gcp_csp(
    mock_scan, mock_put, mock_resolve, client, auth_headers
):
    mock_scan.return_value = SimpleNamespace(is_sensitive=False, reasons=[])
    storage = SimpleNamespace(
        primary_bucket="gcp-vault",
        is_byoc=False,
        region="",
        object_key=lambda username, filename: f"secure/{username}/{filename}",
    )
    mock_resolve.return_value = storage
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.post(
        "/api/security/upload-secure",
        headers=headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"encrypt_manual": "false", "always_ask_encryption": "false", "csp": "GCP"},
    )
    assert response.status_code == 200, response.text
    mock_resolve.assert_called()
    mock_put.assert_called_once()
