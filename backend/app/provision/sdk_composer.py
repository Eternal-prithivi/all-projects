# =============================================================================
# MODULE: provision/sdk_composer.py
# PURPOSE: Fast GCP/Azure provisioning via cloud SDKs (parity with AWS Boto3 path).
# =============================================================================
from __future__ import annotations

from typing import Any, Optional

from app.cloud.providers import normalize_provider
from app.provision.provision_catalog import modules_for_csp
from app.provision.sdk_modules import azure_storage, gcp_gcs
from app.provision.sdk_modules.context import SdkDeployContext

SDK_GCP_MODULES = frozenset({"gcs"})
SDK_AZURE_MODULES = frozenset({"azure_storage"})


def sdk_can_handle(config: dict) -> tuple[bool, set[str]]:
    """True when only SDK-supported modules are enabled for GCP or Azure."""
    csp = normalize_provider(config.get("csp") or "AWS")
    if csp == "AWS":
        return False, set()

    supported = SDK_GCP_MODULES if csp == "GCP" else SDK_AZURE_MODULES
    unsupported: set[str] = set()
    enabled_any = False
    for mod in modules_for_csp(csp):
        if config.get(mod["flag"]):
            enabled_any = True
            if mod["key"] not in supported:
                unsupported.add(mod["key"])
    if not enabled_any:
        return False, {"none"}
    return len(unsupported) == 0, unsupported


def enabled_sdk_modules(config: dict) -> list[str]:
    csp = normalize_provider(config.get("csp") or "AWS")
    if csp == "GCP" and config.get("enable_gcs"):
        return ["gcs"]
    if csp == "Azure" and config.get("enable_azure_storage"):
        return ["azure_storage"]
    return []


def plan_sdk(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    csp = normalize_provider(config.get("csp") or "AWS")
    lines: list[str] = []
    errors: list[str] = []
    for mod in enabled_sdk_modules(config):
        if mod == "gcs":
            result = gcp_gcs.plan_gcs(config, cloud_env)
        else:
            result = azure_storage.plan_azure_storage(config, cloud_env)
        if result.get("error"):
            errors.append(result["error"])
        lines.extend(result.get("lines") or [])

    if errors:
        return {
            "success": False,
            "output": "\n".join(lines),
            "error": errors[0],
            "has_changes": False,
        }
    header = f"Zenith will perform the following actions ({csp} SDK fast path):\n\n"
    return {
        "success": True,
        "output": header + "\n".join(lines) + "\n\nPlan: resources to add.",
        "error": None,
        "has_changes": True,
    }


def apply_sdk(
    config: dict,
    cloud_env: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    ctx = SdkDeployContext.from_dict(existing_ctx)
    steps: list[str] = []
    for mod in enabled_sdk_modules(config):
        if mod == "gcs":
            result = gcp_gcs.apply_gcs(config, cloud_env, ctx)
        else:
            result = azure_storage.apply_azure_storage(config, cloud_env, ctx)
        steps.extend(result.get("steps") or [])
        if not result.get("success"):
            return {
                "success": False,
                "output": "\n".join(steps),
                "error": result.get("error"),
                "sdk_context": ctx.to_dict(),
            }
    steps.append("")
    steps.append("Deployment complete (cloud SDK).")
    return {
        "success": True,
        "output": "\n".join(steps),
        "error": None,
        "sdk_context": ctx.to_dict(),
    }


def destroy_sdk(
    config: dict,
    cloud_env: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    ctx = SdkDeployContext.from_dict(existing_ctx)
    csp = normalize_provider(config.get("csp") or "AWS")
    steps: list[str] = []
    mods = list(reversed(enabled_sdk_modules(config)))
    for mod in mods:
        if mod == "gcs":
            result = gcp_gcs.destroy_gcs(config, cloud_env, ctx)
        else:
            result = azure_storage.destroy_azure_storage(config, cloud_env, ctx)
        steps.extend(result.get("steps") or [])
        if not result.get("success"):
            return {"success": False, "output": "\n".join(steps), "error": result.get("error")}
    return {"success": True, "output": "\n".join(steps), "error": None}


def plan_fast_sdk(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    return plan_sdk(config, cloud_env)


def apply_fast_sdk(
    config: dict,
    cloud_env: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    return apply_sdk(config, cloud_env, existing_ctx)


def destroy_fast_sdk(
    config: dict,
    cloud_env: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    return destroy_sdk(config, cloud_env, existing_ctx)
