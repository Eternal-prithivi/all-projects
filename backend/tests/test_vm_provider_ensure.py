"""Unit tests for VM auto-start / auto-provision on assignment."""

from unittest.mock import patch

import pytest

from app.vm.models import ClusterType
from app.vm import vm_provider
from app.vm.cluster_catalog import cluster_vms, resolve_vm_alias


@pytest.mark.parametrize(
    "vm_loads,expected_name",
    [
        (
            [
                {"vm_name": "general-micro-vm-1", "status": "RUNNING", "active_users": 2, "vm_ip": "1.1.1.1"},
                {"vm_name": "general-small-vm-2", "status": "RUNNING", "active_users": 0, "vm_ip": "2.2.2.2"},
            ],
            "general-small-vm-2",
        ),
        (
            [
                {"vm_name": "storage-small-vm-1", "status": "TERMINATED", "active_users": 0, "vm_ip": "N/A"},
            ],
            "storage-small-vm-1",
        ),
        (
            [
                {"vm_name": "general-micro-aws-vm-1", "status": "NOT_PROVISIONED", "active_users": 0, "vm_ip": "N/A"},
            ],
            "general-micro-aws-vm-1",
        ),
    ],
)
def test_ensure_cluster_vm_for_assignment(vm_loads, expected_name):
    with patch.object(vm_provider, "ensure_vm_running") as mock_ensure:
        mock_ensure.return_value = {"vm_name": expected_name, "vm_ip": "9.9.9.9"}
        cluster = (
            ClusterType.STORAGE
            if expected_name.startswith("storage")
            else ClusterType.GENERAL
        )
        result = vm_provider.ensure_cluster_vm_for_assignment(
            "GCP", cluster, vm_loads
        )
    if vm_loads[0]["status"] == "RUNNING" and len(vm_loads) > 1:
        assert result["vm_name"] == expected_name
        mock_ensure.assert_not_called()
    elif vm_loads[0]["status"] == "RUNNING":
        assert result["vm_name"] == expected_name
    else:
        mock_ensure.assert_called_once()
        assert result["vm_name"] == expected_name
        assert result["vm_ip"] == "9.9.9.9"


@patch.object(vm_provider, "create_vm")
@patch.object(vm_provider, "get_vm_details")
def test_ensure_vm_running_creates_missing(mock_details, mock_create):
    slot = cluster_vms("GCP", ClusterType.GENERAL)[0]
    mock_details.return_value = {
        "name": slot,
        "status": "NOT_PROVISIONED",
        "external_ip": "N/A",
    }
    mock_create.return_value = {
        "name": slot,
        "status": "RUNNING",
        "details": {"external_ip": "3.3.3.3"},
    }
    with patch.object(vm_provider, "count_active_cluster_instances", return_value=0):
        result = vm_provider.ensure_vm_running("GCP", ClusterType.GENERAL, slot)
    assert result == {"vm_name": slot, "vm_ip": "3.3.3.3"}
    mock_create.assert_called_once()


@patch.object(vm_provider, "create_vm")
@patch.object(vm_provider, "delete_vm")
@patch.object(vm_provider, "get_vm_details")
def test_ensure_vm_running_ephemeral_recreates_stopped(
    mock_details, mock_delete, mock_create
):
    slot = cluster_vms("GCP", ClusterType.GENERAL)[0]
    mock_details.return_value = {
        "name": slot,
        "status": "TERMINATED",
        "external_ip": "N/A",
    }
    mock_create.return_value = {
        "name": slot,
        "status": "RUNNING",
        "details": {"external_ip": "4.4.4.4"},
    }
    with patch.object(vm_provider, "count_active_cluster_instances", return_value=0):
        result = vm_provider.ensure_vm_running("GCP", ClusterType.GENERAL, slot)
    assert result == {"vm_name": slot, "vm_ip": "4.4.4.4"}
    mock_delete.assert_called_once()
    mock_create.assert_called_once()


@patch.object(vm_provider, "ensure_vm_running")
def test_ensure_cluster_honors_vm_preference(mock_ensure):
    pool = cluster_vms("GCP", ClusterType.GENERAL)
    loads = [
        {"vm_name": pool[0], "status": "RUNNING", "active_users": 0, "vm_ip": "1.1.1.1"},
        {"vm_name": pool[1], "status": "NOT_PROVISIONED", "active_users": 0, "vm_ip": "N/A"},
    ]
    mock_ensure.return_value = {"vm_name": pool[1], "vm_ip": "2.2.2.2"}
    result = vm_provider.ensure_cluster_vm_for_assignment(
        "GCP",
        ClusterType.GENERAL,
        loads,
        vm_preference=pool[1],
    )
    assert result["vm_name"] == pool[1]
    mock_ensure.assert_called_once_with("GCP", ClusterType.GENERAL, pool[1])


def test_legacy_vm_preference_resolves():
    canonical = resolve_vm_alias("general-vm-2", "GCP")
    assert canonical == "general-small-vm-2"
