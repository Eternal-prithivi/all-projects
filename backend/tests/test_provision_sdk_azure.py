"""Unit tests for Azure SDK provision modules (mocked)."""

from unittest.mock import MagicMock, patch

from app.provision.sdk_modules import azure_vnet
from app.provision.sdk_modules.context import SdkDeployContext


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
