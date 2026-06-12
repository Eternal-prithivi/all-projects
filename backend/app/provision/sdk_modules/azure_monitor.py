"""Azure Monitor action group SDK module."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceNotFoundError

from app.provision.sdk_clients import azure_monitor_client
from app.provision.sdk_modules.azure_resource_group import azure_effective_location, ensure_resource_group
from app.provision.sdk_modules.context import SdkDeployContext

ACTION_GROUP = "zenith-alerts"


def plan_azure_monitor(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    lines = [f"  + azurerm_monitor_action_group.{ACTION_GROUP}"]
    return {"lines": lines, "error": None, "resources": lines}


def apply_azure_monitor(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    email = (config.get("alarm_email") or "").strip()
    if not email:
        return {"success": True, "steps": ["✓ Azure Monitor skipped (no alarm email)"], "error": None}
    ok, steps, err = ensure_resource_group(config, cloud_env, ctx)
    if not ok:
        return {"success": False, "steps": steps, "error": err}
    rg = ctx.azure_resource_group
    location = azure_effective_location(config, ctx)
    client, _, _ = azure_monitor_client(cloud_env)
    try:
        try:
            client.action_groups.get(rg, ACTION_GROUP)
            steps.append(f"✓ Action group '{ACTION_GROUP}' exists")
        except ResourceNotFoundError:
            group = client.action_groups.create_or_update(
                rg,
                ACTION_GROUP,
                {
                    "location": "global",
                    "group_short_name": "zenith",
                    "enabled": True,
                    "email_receivers": [
                        {"name": "admin", "email_address": email, "use_common_alert_schema": True}
                    ],
                },
            )
            ctx.action_group_id = group.id or ACTION_GROUP
            steps.append(f"✓ Action group '{ACTION_GROUP}' for {email}")
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_azure_monitor(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    client, _, _ = azure_monitor_client(cloud_env)
    steps: list[str] = []
    try:
        try:
            client.action_groups.delete(rg, ACTION_GROUP)
            steps.append(f"✓ Deleted action group '{ACTION_GROUP}'")
        except ResourceNotFoundError:
            pass
        return {"success": True, "steps": steps or ["Monitor: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_azure_monitor_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    if not (config.get("alarm_email") or "").strip():
        return 0, []
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    client, _, _ = azure_monitor_client(cloud_env)
    try:
        client.action_groups.get(rg, ACTION_GROUP)
        return 0, []
    except ResourceNotFoundError:
        return 1, ["~ Azure action group missing"]
    except Exception as exc:
        return 1, [f"~ Monitor check failed: {exc}"]
