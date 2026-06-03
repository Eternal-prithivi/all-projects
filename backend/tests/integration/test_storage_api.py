"""Storage API integration smoke tests."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_list_files_empty(client, auth_headers):
    headers, _user = auth_headers()
    response = client.get("/api/storage/files", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


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


@patch("app.storage.routes_storage.list_objects_gcp", return_value=[])
@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_sync_gcp_returns_structure(mock_resolve, _mock_list, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "test-gcp-bucket",
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


@patch("app.storage.routes_storage.list_objects_azure", return_value=[])
@patch("app.storage.routes_storage.resolve_azure_credentials")
def test_sync_azure_returns_structure(mock_resolve, _mock_list, client, auth_headers):
    mock_resolve.return_value = {
        "container_name": "test-container",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post("/api/storage/sync/azure", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "inserted" in body
    assert body["bucket_name"] == "test-container"
