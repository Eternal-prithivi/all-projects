"""Storage API integration smoke tests."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_list_files_empty(client, auth_headers):
    headers, _user = auth_headers()
    response = client.get("/api/storage/files", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_cost_preview_endpoint(client, auth_headers):
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/intelligence/cost-preview",
        headers=headers,
        json={
            "file_size_mb": 512,
            "determined_tier": "warm",
            "user_priority": "cost",
            "user_intent": "archival",
            "lifecycle_policy": "auto",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "cross_cloud" in body
    assert len(body["scenarios"]) == 2


@patch("app.storage.routes_storage.resolve_aws_credentials")
def test_intelligence_summary_endpoint(mock_resolve, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "test-bucket",
        "region": "us-east-1",
    }
    headers, _user = auth_headers()
    response = client.get("/api/storage/intelligence/summary", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "health" in body
    assert "savings" in body
    assert body["health"]["grade"] == "A"


@patch("app.storage.routes_storage.resolve_aws_credentials")
@patch("app.storage.routes_storage.upload_to_aws")
def test_upload_smoke(mock_upload, mock_resolve, client, auth_headers):
    mock_upload.return_value = "user/test.txt"
    mock_resolve.return_value = {
        "access_key_id": "AKIATEST",
        "secret_access_key": "secret",
        "bucket_name": "test-bucket",
        "region": "us-east-1",
        "is_byoc": False,
    }
    headers, _user = auth_headers()

    response = client.post(
        "/api/storage/upload",
        headers=headers,
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"csp": "AWS", "storage_class": "S3 Standard"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["filename"] == "test.txt"


@patch("app.storage.routes_storage.log_ensemble_storage_prediction")
def test_analyze_storage_smoke(_mock_log, client, auth_headers):
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/analyze",
        headers=headers,
        json={
            "filename": "quarterly-report.pdf",
            "file_size_mb": 2.5,
            "user_priority": "balanced",
            "user_intent": "active",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "determined_tier" in body
    assert "recommendation" in body
    assert "workflow" in body
    assert len(body["workflow"]) == 5
    assert body["workflow"][0]["name"] == "task_arrival_preprocessing"


@patch("app.storage.routes_storage.list_objects_aws", return_value=[])
@patch("app.storage.routes_storage.resolve_aws_credentials")
def test_sync_aws_returns_structure(mock_resolve, _mock_list, client, auth_headers):
    mock_resolve.return_value = {
        "access_key_id": "AKIATEST",
        "secret_access_key": "secret",
        "bucket_name": "test-bucket",
        "region": "us-east-1",
        "is_byoc": False,
    }

    headers, _user = auth_headers()
    response = client.post("/api/storage/sync/aws", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "inserted" in body
    assert "bucket_name" in body


@patch("app.storage.routes_storage.resolve_platform_storage_target", return_value=None)
@patch("app.storage.routes_storage.list_objects_gcp", return_value=[])
@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_sync_gcp_returns_structure(mock_resolve, _mock_list, _mock_platform, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "test-gcp-bucket",
        "service_account_key_path": "/tmp/fake-sa.json",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post("/api/storage/sync/gcp", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "inserted" in body
    assert body["bucket_name"] == "test-gcp-bucket"


@patch("app.storage.routes_storage.upload_to_gcp", return_value="user/gcp-smoke.txt")
@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_upload_gcp_smoke(mock_resolve, mock_upload, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "test-gcp-bucket",
        "service_account_key_path": "/tmp/fake-sa.json",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/upload",
        headers=headers,
        files={"file": ("gcp-smoke.txt", b"hello", "text/plain")},
        data={"csp": "GCP", "storage_class": "STANDARD"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["filename"] == "gcp-smoke.txt"
    assert response.json()["csp"] == "GCP"


@patch("app.storage.routes_storage.upload_to_gcp", return_value="user/other-gcp.txt")
@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_upload_gcp_with_bucket_override(mock_resolve, mock_upload, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "default-gcp-bucket",
        "service_account_key_path": "/tmp/fake-sa.json",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/upload",
        headers=headers,
        files={"file": ("other-gcp.txt", b"hello", "text/plain")},
        data={"csp": "GCP", "storage_class": "STANDARD", "bucket": "other-gcp-bucket"},
    )
    assert response.status_code == 201, response.text
    mock_upload.assert_called_once()
    assert mock_upload.call_args.kwargs["bucket_name"] == "other-gcp-bucket"
    assert response.json()["bucket"] == "other-gcp-bucket"


@patch("app.storage.routes_storage.upload_to_azure", return_value="user/azure-smoke.txt")
@patch("app.storage.routes_storage.resolve_azure_credentials")
def test_upload_azure_smoke(mock_resolve, mock_upload, client, auth_headers):
    mock_resolve.return_value = {
        "container_name": "test-container",
        "account_name": "acct",
        "account_key": "key",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/upload",
        headers=headers,
        files={"file": ("azure-smoke.txt", b"hello", "text/plain")},
        data={"csp": "Azure", "storage_class": "Hot Blob Storage"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["csp"] == "Azure"
    mock_upload.assert_called_once()


@patch("app.storage.routes_storage.delete_from_gcp")
@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_delete_gcp_smoke(mock_resolve, mock_delete, client, auth_headers, db):
    mock_resolve.return_value = {"bucket_name": "b", "is_byoc": False}
    headers, user = auth_headers()
    db["files"].insert_one(
        {
            "filename": "gcp-del.txt",
            "s3_key": f"{user['username']}/gcp-del.txt",
            "owner_username": user["username"],
            "csp": "GCP",
            "storage_class": "STANDARD",
            "cloud_bucket": "test-gcp-bucket",
        }
    )
    response = client.delete("/api/storage/delete/gcp-del.txt", headers=headers)
    assert response.status_code == 200, response.text
    mock_delete.assert_called_once()


@patch("app.storage.routes_storage.get_download_url_from_azure", return_value="https://azure.example/sas")
@patch("app.storage.routes_storage.resolve_azure_credentials")
def test_download_azure_smoke(mock_resolve, mock_url, client, auth_headers, db):
    mock_resolve.return_value = {
        "container_name": "c",
        "account_name": "a",
        "account_key": "k",
        "is_byoc": False,
    }
    headers, user = auth_headers()
    db["files"].insert_one(
        {
            "filename": "azure-dl.txt",
            "s3_key": f"{user['username']}/azure-dl.txt",
            "owner_username": user["username"],
            "csp": "Azure",
            "storage_class": "Hot",
            "cloud_bucket": "c",
        }
    )
    response = client.get("/api/storage/download/azure-dl.txt", headers=headers)
    assert response.status_code == 200, response.text
    assert "presigned_url" in response.json()
    mock_url.assert_called_once()


@patch("app.storage.routes_storage.initiate_glacier_restore_aws", return_value={"message": "Restore started"})
@patch("app.storage.routes_storage.resolve_aws_credentials")
def test_restore_aws_route(mock_resolve, mock_restore, client, auth_headers, db):
    mock_resolve.return_value = {
        "access_key_id": "x",
        "secret_access_key": "y",
        "bucket_name": "b",
        "region": "us-east-1",
        "is_byoc": False,
    }
    headers, user = auth_headers()
    db["files"].insert_one(
        {
            "filename": "cold.txt",
            "s3_key": f"{user['username']}/cold.txt",
            "owner_username": user["username"],
            "csp": "AWS",
            "storage_class": "GLACIER",
            "cloud_bucket": "b",
        }
    )
    response = client.post(
        "/api/storage/restore/AWS/cold.txt",
        headers=headers,
        data={"tier": "Standard", "days": "3"},
    )
    assert response.status_code == 202, response.text
    mock_restore.assert_called_once()


@patch("app.storage.routes_storage.initiate_archive_restore_gcp", return_value={"message": "GCP restore started"})
def test_restore_gcp_route(mock_restore, client, auth_headers, db):
    headers, user = auth_headers()
    db["files"].insert_one(
        {
            "filename": "archived.gcs",
            "s3_key": f"{user['username']}/archived.gcs",
            "owner_username": user["username"],
            "csp": "GCP",
            "storage_class": "ARCHIVE",
            "cloud_bucket": "zeneith-main-asia",
        }
    )
    response = client.post("/api/storage/restore/GCP/archived.gcs", headers=headers)
    assert response.status_code == 202, response.text
    assert response.json()["provider"] == "gcp"
    mock_restore.assert_called_once()


@patch("app.storage.routes_storage.initiate_archive_restore_azure", return_value={"message": "Azure restore started"})
def test_restore_azure_route(mock_restore, client, auth_headers, db):
    headers, user = auth_headers()
    db["files"].insert_one(
        {
            "filename": "archived.blob",
            "s3_key": f"{user['username']}/archived.blob",
            "owner_username": user["username"],
            "csp": "Azure",
            "storage_class": "Archive",
            "cloud_bucket": "zenith-storage",
            "cloud_account": "zenithstorageasia",
        }
    )
    response = client.post(
        "/api/storage/restore/Azure/archived.blob",
        headers=headers,
        data={"tier": "High", "days": "1"},
    )
    assert response.status_code == 202, response.text
    assert response.json()["provider"] == "azure"
    mock_restore.assert_called_once()


@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_sync_gcp_missing_config(mock_resolve, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "",
        "service_account_key_path": "",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post("/api/storage/sync/gcp", headers=headers)
    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert detail["status"] == "missing_config"
    assert detail["provider"] == "gcp"


@patch("app.storage.routes_storage.resolve_platform_storage_target", return_value=None)
@patch("app.storage.routes_storage.list_objects_azure", return_value=[])
@patch("app.storage.routes_storage.resolve_azure_credentials")
def test_sync_azure_returns_structure(mock_resolve, _mock_list, _mock_platform, client, auth_headers):
    mock_resolve.return_value = {
        "container_name": "test-container",
        "account_name": "acct",
        "account_key": "key",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post("/api/storage/sync/azure", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "inserted" in body
    assert body["bucket_name"] == "test-container"
