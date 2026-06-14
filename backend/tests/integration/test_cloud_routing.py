"""Tri-cloud API routing smoke tests — endpoints exist and dispatch (mocked)."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_cost_tri_cloud_routes_registered(client, auth_headers):
    """Cost module exposes per-provider routes (auth required)."""
    headers, _user = auth_headers()
    for path in ("/api/cost/aws", "/api/cost/gcp", "/api/cost/azure"):
        response = client.get(
            path,
            headers=headers,
            params={"start_date": "2026-01-01", "end_date": "2026-01-07"},
        )
        assert response.status_code != 404, path


@patch("app.cost.routes_cost.get_gcp_billing_data")
@patch("app.cloud.availability.assert_provider_available")
@patch("app.byoc.capabilities.assert_byoc_feature_ready")
def test_cost_gcp_route_returns_provider(
    _mock_byoc_ready, _mock_provider, mock_fetch, client, auth_headers
):
    mock_fetch.return_value = {"status": "missing_config", "message": "mock"}
    headers, _user = auth_headers()
    response = client.get(
        "/api/cost/gcp",
        headers=headers,
        params={"start_date": "2026-01-01", "end_date": "2026-01-07"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["provider"] == "gcp"


@patch("app.cost.routes_cost.get_azure_billing_data")
def test_cost_azure_route_returns_provider(mock_fetch, client, auth_headers):
    mock_fetch.return_value = {"status": "missing_config", "message": "mock"}
    headers, _user = auth_headers()
    response = client.get(
        "/api/cost/azure",
        headers=headers,
        params={"start_date": "2026-01-01", "end_date": "2026-01-07"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["provider"] == "azure"


@patch("app.storage.routes_storage.upload_to_gcp", return_value="user/gcp-file.txt")
@patch("app.storage.routes_storage.resolve_gcp_credentials")
def test_upload_gcp_routing(mock_resolve, mock_upload, client, auth_headers):
    mock_resolve.return_value = {
        "bucket_name": "test-gcp-bucket",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/upload",
        headers=headers,
        files={"file": ("gcp.txt", b"data", "text/plain")},
        data={"csp": "gcp", "storage_class": "STANDARD"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["csp"] == "GCP"
    mock_upload.assert_called_once()


@patch("app.storage.routes_storage.upload_to_azure", return_value="user/azure-file.txt")
@patch("app.storage.routes_storage.resolve_azure_credentials")
def test_upload_azure_routing(mock_resolve, mock_upload, client, auth_headers):
    mock_resolve.return_value = {
        "container_name": "test-container",
        "is_byoc": False,
    }
    headers, _user = auth_headers()
    response = client.post(
        "/api/storage/upload",
        headers=headers,
        files={"file": ("azure.txt", b"data", "text/plain")},
        data={"csp": "Azure", "storage_class": "Hot"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["csp"] == "Azure"
    mock_upload.assert_called_once()


def test_storage_sync_routes_exist(client, auth_headers):
    headers, _user = auth_headers()
    for path in (
        "/api/storage/sync/aws",
        "/api/storage/sync/gcp",
        "/api/storage/sync/azure",
    ):
        response = client.post(path, headers=headers)
        assert response.status_code != 404, path
