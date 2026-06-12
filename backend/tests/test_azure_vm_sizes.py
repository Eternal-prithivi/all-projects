"""Azure VM size discovery for regional capacity."""

from unittest.mock import MagicMock

from app.provision.sdk_modules.azure_vm_sizes import (
    azure_vm_sizes_for_deploy,
    discover_azure_x64_vm_sizes,
)


def _cap(key: str, value: str):
    cap = MagicMock()
    cap.name = key
    cap.value = value
    return cap


def _sku(name: str, *, vcpus: str = "1", arch: str = "x64", restricted: bool = False):
    sku = MagicMock()
    sku.resource_type = "virtualMachines"
    sku.name = name
    sku.capabilities = [
        _cap("vCPUs", vcpus),
        _cap("CpuArchitectureType", arch),
    ]
    if restricted:
        restriction = MagicMock()
        restriction.type = "Location"
        restriction.reason_code = "NotAvailableForSubscription"
        sku.restrictions = [restriction]
    else:
        sku.restrictions = []
    return sku


def test_discover_filters_arm_and_restricted():
    client = MagicMock()
    client.resource_skus.list.return_value = [
        _sku("Standard_B1s"),
        _sku("Standard_B2pts_v2", arch="Arm64"),
        _sku("Standard_D2s_v3", vcpus="2"),
        _sku("Standard_B2s", restricted=True),
    ]
    sizes = discover_azure_x64_vm_sizes(client, "centralus")
    assert "Standard_B1s" in sizes
    assert "Standard_D2s_v3" in sizes
    assert "Standard_B2pts_v2" not in sizes
    assert "Standard_B2s" not in sizes


def test_deploy_sizes_merge_preferred_and_discovered():
    client = MagicMock()
    client.resource_skus.list.return_value = [
        _sku("Standard_D2as_v5", vcpus="2"),
        _sku("Standard_F2s_v2", vcpus="2"),
    ]
    sizes = azure_vm_sizes_for_deploy(client, "centralus", "Standard_B1s")
    assert sizes[0] == "Standard_B1s"
    assert "Standard_D2as_v5" in sizes
    assert "Standard_F2s_v2" in sizes
