"""Azure resource group helper for SDK provision modules."""

from __future__ import annotations

from typing import Any

from app.provision.sdk_clients import azure_resource_client
from app.provision.sdk_modules.context import SdkDeployContext


def ensure_resource_group(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[bool, list[str], str | None]:
    rg = config.get("resource_group_name") or ctx.azure_resource_group or "zenith-rg"
    location = config.get("azure_location") or "eastus"
    steps: list[str] = []
    try:
        client, _, _ = azure_resource_client(cloud_env)
        client.resource_groups.create_or_update(rg, {"location": location})
        ctx.azure_resource_group = rg
        steps.append(f"✓ Resource group '{rg}'")
        return True, steps, None
    except Exception as exc:
        return False, steps, str(exc)


def plan_resource_group(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    rg = config.get("resource_group_name") or "zenith-rg"
    location = config.get("azure_location") or "eastus"
    return {
        "lines": [f"  + azurerm_resource_group.main ({rg}, {location})"],
        "error": None,
        "resources": [f"resource_group:{rg}"],
    }


def destroy_resource_group_if_empty(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    rg = config.get("resource_group_name") or ctx.azure_resource_group or ""
    if not rg:
        return {"success": True, "steps": ["Resource group: nothing to delete"], "error": None}
    steps: list[str] = []
    try:
        client, _, subscription = azure_resource_client(cloud_env)
        client.resource_groups.begin_delete(rg)
        steps.append(f"✓ Deleting resource group '{rg}' (async)")
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}
