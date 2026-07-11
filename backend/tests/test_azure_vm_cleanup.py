"""Tests for Azure VM attached-resource cleanup."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.vm.azure_cleanup import (
    cleanup_vm_attached_resources,
    collect_managed_disk_ids,
    disks_linked_to_vm,
    os_disk_name,
    os_disk_profile,
)


def test_os_disk_profile_sets_delete_option_and_name():
    profile = os_disk_profile(32, "Standard_LRS", "general-micro-azure-vm-1")
    assert profile["name"] == "general-micro-azure-vm-1-osdisk"
    assert profile["delete_option"] == "Delete"
    assert profile["disk_size_gb"] == 32


def test_collect_managed_disk_ids_reads_os_and_data_disks():
    vm = SimpleNamespace(
        storage_profile=SimpleNamespace(
            os_disk=SimpleNamespace(
                managed_disk=SimpleNamespace(id="/subscriptions/s/resourceGroups/rg/providers/Microsoft.Compute/disks/os1")
            ),
            data_disks=[
                SimpleNamespace(
                    managed_disk=SimpleNamespace(
                        id="/subscriptions/s/resourceGroups/rg/providers/Microsoft.Compute/disks/data1"
                    )
                )
            ],
        )
    )
    ids = collect_managed_disk_ids(vm)
    assert len(ids) == 2
    assert ids[0].endswith("/disks/os1")
    assert ids[1].endswith("/disks/data1")


def test_disks_linked_to_vm_matches_zenith_and_azure_names():
    compute_client = MagicMock()
    compute_client.disks.list_by_resource_group.return_value = [
        SimpleNamespace(name="vm1-osdisk"),
        SimpleNamespace(name="vm1_OsDisk_1_abcd"),
        SimpleNamespace(name="unrelated-disk"),
    ]
    names = disks_linked_to_vm(compute_client, "zenith-rg", "vm1")
    assert "vm1-osdisk" in names
    assert "vm1_OsDisk_1_abcd" in names
    assert "unrelated-disk" not in names


def test_cleanup_vm_attached_resources_deletes_nic_pip_and_disks():
    compute_client = MagicMock()
    network_client = MagicMock()
    compute_client.virtual_machines.get.side_effect = Exception("not found")
    compute_client.disks.list_by_resource_group.return_value = [
        SimpleNamespace(name=f"{os_disk_name('slot-a')}")
    ]

    nic_delete = MagicMock()
    nic_delete.result.return_value = None
    network_client.network_interfaces.begin_delete.return_value = nic_delete

    pip_delete = MagicMock()
    pip_delete.result.return_value = None
    network_client.public_ip_addresses.begin_delete.return_value = pip_delete

    disk_delete = MagicMock()
    disk_delete.result.return_value = None
    compute_client.disks.begin_delete.return_value = disk_delete

    result = cleanup_vm_attached_resources(
        compute_client,
        network_client,
        "zenith-rg",
        "slot-a",
    )

    assert result["nic_deleted"] is True
    assert result["pip_deleted"] is True
    assert result["disks_deleted"] is True
    network_client.network_interfaces.begin_delete.assert_called_once_with(
        "zenith-rg",
        "slot-a-nic",
    )
    network_client.public_ip_addresses.begin_delete.assert_called_once_with(
        "zenith-rg",
        "slot-a-pip",
    )
    compute_client.disks.begin_delete.assert_called_once_with(
        "zenith-rg",
        "slot-a-osdisk",
    )
