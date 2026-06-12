"""Unit tests for Azure SDK provision modules (mocked)."""

from unittest.mock import MagicMock, patch

from app.provision.sdk_modules import azure_vnet
from app.provision.sdk_modules.azure_vm import AZURE_PUBLIC_IP_SKU, azure_public_ip_params
from app.provision.sdk_modules.common import (
    azure_vm_sizes_to_try,
    is_azure_sku_capacity_error,
    is_azure_vm_architecture_error,
)
from app.provision.sdk_modules.context import SdkDeployContext


def test_azure_vm_size_fallbacks_are_x64_only():
    sizes = azure_vm_sizes_to_try("Standard_B1s")
    assert sizes[0] == "Standard_B1s"
    assert "Standard_B1ms" in sizes
    assert not any("pts" in s or "ats" in s for s in sizes)


def test_is_azure_vm_architecture_error():
    err = Exception(
        "Cannot create a VM of size 'Standard_B2pts_v2' because this VM size only "
        "supports a CPU Architecture of 'Arm64', but an image or disk with CPU "
        "Architecture 'x64' was given."
    )
    assert is_azure_vm_architecture_error(err)


def test_is_azure_sku_capacity_error_from_message():
    assert is_azure_sku_capacity_error(Exception("SkuNotAvailable: Capacity Restrictions"))


def test_azure_public_ip_uses_standard_sku():
    params = azure_public_ip_params("eastus")
    assert params["sku"]["name"] == AZURE_PUBLIC_IP_SKU
    assert params["sku"]["name"] == "Standard"
    assert params["public_ip_allocation_method"] == "Static"


def test_plan_vnet_lines():
    result = azure_vnet.plan_vnet({}, {})
    assert result["error"] is None
    assert "zenith-vnet" in result["lines"][0]


@patch("app.provision.sdk_modules.azure_vnet.ensure_resource_group")
@patch("app.provision.sdk_modules.azure_vnet.azure_network_client")
def test_apply_vnet_success(mock_net_client, mock_ensure_rg):
    mock_ensure_rg.return_value = (True, ["✓ Resource group"], None)
    network_client = MagicMock()
    mock_net_client.return_value = (network_client, None, None)
    from azure.core.exceptions import ResourceNotFoundError

    network_client.virtual_networks.get.side_effect = ResourceNotFoundError("missing")
    network_client.subnets.get.side_effect = ResourceNotFoundError("missing")
    network_client.virtual_networks.begin_create_or_update.return_value.result.return_value = None
    network_client.subnets.begin_create_or_update.return_value.result.return_value = None
    ctx = SdkDeployContext()
    ctx.azure_resource_group = "zenith-rg"
    result = azure_vnet.apply_vnet({"azure_location": "eastus"}, {}, ctx)
    assert result["success"] is True
    assert ctx.vnet_name == "zenith-vnet"
