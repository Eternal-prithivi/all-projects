"""Integration tests for expanded VM cluster APIs."""

from unittest.mock import MagicMock, patch

import pytest

from app.vm.cluster_catalog import cluster_types

pytestmark = pytest.mark.integration


@patch("app.vm.routes_vm.DB")
@patch("app.vm.vm_provider.get_vm_details")
def test_vm_clusters_metadata(mock_details, mock_db, client, auth_headers):
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.get("/api/vm/clusters?csp=GCP", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("topology") == "ring"
    clusters = body.get("clusters", [])
    assert len(clusters) == 7
    assert all(len(c.get("slots", [])) == 4 for c in clusters)


@patch("app.vm.routes_vm.DB")
@patch("app.vm.vm_provider.get_vm_details")
def test_vm_pool_returns_seven_clusters_four_slots(
    mock_details, mock_db, client, auth_headers
):
    mock_details.return_value = {"status": "NOT_PROVISIONED", "machine_type": ""}
    mock_coll = MagicMock()
    mock_coll.count_documents.return_value = 0
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.get("/api/vm/pool?csp=GCP", headers=headers)
    assert response.status_code == 200, response.text
    clusters = response.json().get("clusters", {})
    assert len(clusters) == len(list(cluster_types()))
    for cluster_type in cluster_types():
        key = cluster_type.value
        assert key in clusters
        assert len(clusters[key]["slots"]) == 4


@patch("app.vm.routes_vm.DB")
@patch("app.vm.vm_provider.get_vm_details")
def test_vm_config_unprovisioned_slot_returns_catalog_spec(
    mock_details, mock_db, client, auth_headers
):
    mock_details.return_value = {"status": "NOT_PROVISIONED", "machine_type": ""}
    mock_coll = MagicMock()
    mock_coll.count_documents.return_value = 0
    mock_coll.find_one.return_value = None
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)

    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.get(
        "/api/vm/config/general-micro-vm-1?csp=GCP",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "NOT_PROVISIONED"
    assert body["tier"] == "micro"
    assert body["cluster_type"] == "GENERAL"
    assert body.get("machine_type")
