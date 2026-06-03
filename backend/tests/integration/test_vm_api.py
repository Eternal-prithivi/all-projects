"""VM API integration tests — AWS/GCP provider dispatch."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_vm_status_requires_auth(client):
    response = client.get("/api/vm/status")
    assert response.status_code == 401


@patch("app.vm.vm_provider.list_vms", return_value=[])
@patch("app.vm.vm_provider.cluster_vms", return_value=["general-aws-vm-1"])
def test_vm_status_aws_query(mock_cluster, mock_list, client, auth_headers):
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.get("/api/vm/status?csp=AWS", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("csp") == "AWS"
    mock_list.assert_called()


@patch("app.vm.routes_vm.assign_vm_to_user")
def test_vm_request_aws_csp(mock_assign, client, auth_headers):
    mock_assign.return_value = (
        "general-aws-vm-1",
        "1.2.3.4",
        "ssh user@1.2.3.4",
        __import__("app.vm.models", fromlist=["ClusterType"]).ClusterType.GENERAL,
        __import__("datetime").datetime.utcnow(),
        __import__("datetime").datetime.utcnow(),
    )
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.post(
        "/api/vm/request",
        headers=headers,
        json={
            "csp": "AWS",
            "workload_description": "web API with PostgreSQL backend",
            "priority_level": 1,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["csp"] == "AWS"
    assert mock_assign.call_args.kwargs.get("csp") == "AWS"


@patch("app.vm.routes_vm.assign_vm_to_user")
def test_vm_request_azure_csp(mock_assign, client, auth_headers):
    mock_assign.return_value = (
        "general-azure-vm-1",
        "10.0.0.4",
        "ssh azureuser@10.0.0.4",
        __import__("app.vm.models", fromlist=["ClusterType"]).ClusterType.GENERAL,
        __import__("datetime").datetime.utcnow(),
        __import__("datetime").datetime.utcnow(),
    )
    headers, _user = auth_headers(two_fa_enabled=False)
    response = client.post(
        "/api/vm/request",
        headers=headers,
        json={
            "csp": "Azure",
            "workload_description": "batch job",
            "priority_level": 1,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["csp"] == "Azure"
    assert mock_assign.call_args.kwargs.get("csp") == "Azure"
