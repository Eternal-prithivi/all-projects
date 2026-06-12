"""Azure Virtual Network + subnet SDK module."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceNotFoundError

from app.provision.sdk_clients import azure_network_client
from app.provision.sdk_modules.azure_resource_group import azure_effective_location, ensure_resource_group
from app.provision.sdk_modules.context import SdkDeployContext

VNET_NAME = "zenith-vnet"
SUBNET_NAME = "zenith-subnet"


def plan_vnet(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    lines = [
        f"  + azurerm_virtual_network.{VNET_NAME}",
        f"  + azurerm_subnet.{SUBNET_NAME}",
    ]
    return {"lines": lines, "error": None, "resources": lines}


def apply_vnet(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    ok, steps, err = ensure_resource_group(config, cloud_env, ctx)
    if not ok:
        return {"success": False, "steps": steps, "error": err}
    rg = ctx.azure_resource_group
    location = azure_effective_location(config, ctx)
    network_client, _, _ = azure_network_client(cloud_env)
    try:
        try:
            network_client.virtual_networks.get(rg, VNET_NAME)
        except ResourceNotFoundError:
            network_client.virtual_networks.begin_create_or_update(
                rg,
                VNET_NAME,
                {
                    "location": location,
                    "address_space": {"address_prefixes": ["10.0.0.0/16"]},
                },
            ).result()
        steps.append(f"✓ Virtual network '{VNET_NAME}'")
        ctx.vnet_name = VNET_NAME

        try:
            network_client.subnets.get(rg, VNET_NAME, SUBNET_NAME)
        except ResourceNotFoundError:
            network_client.subnets.begin_create_or_update(
                rg,
                VNET_NAME,
                SUBNET_NAME,
                {"address_prefix": "10.0.1.0/24"},
            ).result()
        steps.append(f"✓ Subnet '{SUBNET_NAME}'")
        ctx.subnet_name = SUBNET_NAME
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_vnet(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    network_client, _, _ = azure_network_client(cloud_env)
    steps: list[str] = []
    try:
        vnet = ctx.vnet_name or VNET_NAME
        try:
            network_client.virtual_networks.begin_delete(rg, vnet).result()
            steps.append(f"✓ Deleted VNet '{vnet}'")
        except ResourceNotFoundError:
            pass
        return {"success": True, "steps": steps or ["VNet: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_vnet_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    network_client, _, _ = azure_network_client(cloud_env)
    try:
        network_client.virtual_networks.get(rg, ctx.vnet_name or VNET_NAME)
        return 0, []
    except ResourceNotFoundError:
        return 1, ["~ Azure VNet missing"]
    except Exception as exc:
        return 1, [f"~ VNet check failed: {exc}"]
