"""Azure resource group helper for SDK provision modules."""

from __future__ import annotations

import re
from typing import Any

from azure.core.exceptions import ResourceNotFoundError

from app.provision.sdk_clients import azure_resource_client
from app.provision.sdk_modules.context import SdkDeployContext


def normalize_azure_location(location: str | None) -> str:
    return re.sub(r"\s+", "", (location or "").lower())


def region_scoped_resource_group(base: str, location: str) -> str:
    """Derive a per-region RG name, e.g. zenith-rg + centralus → zenith-rg-centralus."""
    name = (base or "zenith-rg").strip() or "zenith-rg"
    loc = normalize_azure_location(location)
    suffix = f"-{loc}"
    if name.lower().endswith(suffix):
        return name
    return f"{name}{suffix}"


def azure_effective_location(config: dict, ctx: SdkDeployContext) -> str:
    """Location resolved from an existing RG or wizard config."""
    return (
        (ctx.azure_location or "").strip()
        or (config.get("azure_location") or "").strip()
        or "eastus"
    )


def resolve_azure_resource_group(
    client: Any,
    config: dict,
) -> tuple[str, str, list[str]]:
    """
    Pick a resource group + location that won't conflict with Azure RG immutability.

    - RG does not exist → use requested name + location.
    - RG exists and location matches → reuse it.
    - RG exists in another region → use {name}-{region} for the requested region.
    """
    notes: list[str] = []
    requested_rg = (config.get("resource_group_name") or "zenith-rg").strip() or "zenith-rg"
    requested_loc = (config.get("azure_location") or "eastus").strip() or "eastus"

    try:
        existing = client.resource_groups.get(requested_rg)
        existing_loc = existing.location or requested_loc
        if normalize_azure_location(existing_loc) == normalize_azure_location(requested_loc):
            return requested_rg, existing_loc, notes
        scoped = region_scoped_resource_group(requested_rg, requested_loc)
        try:
            scoped_rg = client.resource_groups.get(scoped)
            notes.append(
                f"Resource group '{requested_rg}' is in {existing_loc}; "
                f"using existing '{scoped}' in {scoped_rg.location}."
            )
            return scoped, scoped_rg.location or requested_loc, notes
        except ResourceNotFoundError:
            notes.append(
                f"Resource group '{requested_rg}' already exists in {existing_loc}; "
                f"will create '{scoped}' in {requested_loc}."
            )
            return scoped, requested_loc, notes
    except ResourceNotFoundError:
        return requested_rg, requested_loc, notes


def ensure_resource_group(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[bool, list[str], str | None]:
    steps: list[str] = []
    try:
        client, _, _ = azure_resource_client(cloud_env)
        rg, location, notes = resolve_azure_resource_group(client, config)
        steps.extend(notes)

        try:
            existing = client.resource_groups.get(rg)
            ctx.azure_resource_group = rg
            ctx.azure_location = existing.location or location
            steps.append(f"✓ Resource group '{rg}' ({ctx.azure_location})")
            return True, steps, None
        except ResourceNotFoundError:
            client.resource_groups.create_or_update(rg, {"location": location})
            ctx.azure_resource_group = rg
            ctx.azure_location = location
            steps.append(f"✓ Resource group '{rg}' ({location})")
            return True, steps, None
    except Exception as exc:
        msg = str(exc)
        if "InvalidResourceGroupLocation" in msg:
            msg = (
                "Azure resource group region conflict. Zenith should auto-resolve this — "
                "retry Apply, or set a unique resource group name per region "
                "(e.g. zenith-rg-centralus)."
            )
        return False, steps, msg


def plan_resource_group(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    rg = config.get("resource_group_name") or "zenith-rg"
    location = config.get("azure_location") or "eastus"
    scoped = region_scoped_resource_group(rg, location)
    line = f"  + azurerm_resource_group.main ({scoped}, {location})"
    if scoped != rg:
        line += f" [or reuse {rg} if already in {location}]"
    return {
        "lines": [line],
        "error": None,
        "resources": [f"resource_group:{scoped}"],
    }


def destroy_resource_group_if_empty(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    rg = ctx.azure_resource_group or config.get("resource_group_name") or ""
    if not rg:
        return {"success": True, "steps": ["Resource group: nothing to delete"], "error": None}
    steps: list[str] = []
    try:
        client, _, _ = azure_resource_client(cloud_env)
        client.resource_groups.begin_delete(rg)
        steps.append(f"✓ Deleting resource group '{rg}' (async)")
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}
