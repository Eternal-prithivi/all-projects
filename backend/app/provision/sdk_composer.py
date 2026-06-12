# =============================================================================
# MODULE: provision/sdk_composer.py
# PURPOSE: Fast GCP/Azure provisioning via cloud SDKs (parity with AWS Boto3 path).
# =============================================================================
from __future__ import annotations

from typing import Any, Callable, Optional

from app.cloud.providers import normalize_provider
from app.provision.provision_catalog import modules_for_csp
from app.provision.sdk_modules import (
    azure_cosmos,
    azure_monitor,
    azure_storage,
    azure_vm,
    azure_vnet,
    gcp_firestore,
    gcp_gce,
    gcp_gcs,
    gcp_monitoring,
    gcp_network,
    gcp_service_account,
)
from app.provision.sdk_modules.context import SdkDeployContext

SDK_GCP_MODULES = frozenset({
    "gcs", "gcp_network", "gce", "gcp_service_account", "gcp_monitoring", "firestore",
})
SDK_AZURE_MODULES = frozenset({
    "azure_storage", "vnet", "azure_vm", "azure_monitor", "cosmos",
})

GCP_MODULE_FLAGS: dict[str, str] = {
    "gcp_network": "enable_gcp_network",
    "gce": "enable_gce",
    "gcp_service_account": "enable_gcp_service_account",
    "gcp_monitoring": "enable_gcp_monitoring",
    "gcs": "enable_gcs",
    "firestore": "enable_firestore",
}

AZURE_MODULE_FLAGS: dict[str, str] = {
    "vnet": "enable_vnet",
    "azure_vm": "enable_azure_vm",
    "azure_monitor": "enable_azure_monitor",
    "azure_storage": "enable_azure_storage",
    "cosmos": "enable_cosmos",
}

GCP_APPLY_ORDER = ("gcp_network", "gcs", "gcp_service_account", "gce", "gcp_monitoring", "firestore")
GCP_DESTROY_ORDER = ("firestore", "gcp_monitoring", "gce", "gcp_service_account", "gcs", "gcp_network")

AZURE_APPLY_ORDER = ("vnet", "azure_storage", "azure_vm", "azure_monitor", "cosmos")
AZURE_DESTROY_ORDER = ("cosmos", "azure_monitor", "azure_vm", "azure_storage", "vnet")

_GCP_PLAN: dict[str, Callable] = {
    "gcp_network": gcp_network.plan_gcp_network,
    "gce": gcp_gce.plan_gce,
    "gcp_service_account": gcp_service_account.plan_gcp_service_account,
    "gcp_monitoring": gcp_monitoring.plan_gcp_monitoring,
    "gcs": gcp_gcs.plan_gcs,
    "firestore": gcp_firestore.plan_firestore,
}
_GCP_APPLY: dict[str, Callable] = {
    "gcp_network": gcp_network.apply_gcp_network,
    "gce": gcp_gce.apply_gce,
    "gcp_service_account": gcp_service_account.apply_gcp_service_account,
    "gcp_monitoring": gcp_monitoring.apply_gcp_monitoring,
    "gcs": gcp_gcs.apply_gcs,
    "firestore": gcp_firestore.apply_firestore,
}
_GCP_DESTROY: dict[str, Callable] = {
    "gcp_network": gcp_network.destroy_gcp_network,
    "gce": gcp_gce.destroy_gce,
    "gcp_service_account": gcp_service_account.destroy_gcp_service_account,
    "gcp_monitoring": gcp_monitoring.destroy_gcp_monitoring,
    "gcs": gcp_gcs.destroy_gcs,
    "firestore": gcp_firestore.destroy_firestore,
}

_AZURE_PLAN: dict[str, Callable] = {
    "vnet": azure_vnet.plan_vnet,
    "azure_vm": azure_vm.plan_azure_vm,
    "azure_monitor": azure_monitor.plan_azure_monitor,
    "azure_storage": azure_storage.plan_azure_storage,
    "cosmos": azure_cosmos.plan_cosmos,
}
_AZURE_APPLY: dict[str, Callable] = {
    "vnet": azure_vnet.apply_vnet,
    "azure_vm": azure_vm.apply_azure_vm,
    "azure_monitor": azure_monitor.apply_azure_monitor,
    "azure_storage": azure_storage.apply_azure_storage,
    "cosmos": azure_cosmos.apply_cosmos,
}
_AZURE_DESTROY: dict[str, Callable] = {
    "vnet": azure_vnet.destroy_vnet,
    "azure_vm": azure_vm.destroy_azure_vm,
    "azure_monitor": azure_monitor.destroy_azure_monitor,
    "azure_storage": azure_storage.destroy_azure_storage,
    "cosmos": azure_cosmos.destroy_cosmos,
}


def _module_flags(csp: str) -> dict[str, str]:
    if normalize_provider(csp) == "GCP":
        return GCP_MODULE_FLAGS
    return AZURE_MODULE_FLAGS


def enabled_sdk_modules(config: dict) -> list[str]:
    csp = normalize_provider(config.get("csp") or "AWS")
    flags = _module_flags(csp)
    order = GCP_APPLY_ORDER if csp == "GCP" else AZURE_APPLY_ORDER
    enabled = {k for k, flag in flags.items() if config.get(flag)}
    return [m for m in order if m in enabled]


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


def _handlers(csp: str) -> tuple[dict, dict, dict, tuple]:
    if normalize_provider(csp) == "GCP":
        return _GCP_PLAN, _GCP_APPLY, _GCP_DESTROY, GCP_APPLY_ORDER
    return _AZURE_PLAN, _AZURE_APPLY, _AZURE_DESTROY, AZURE_APPLY_ORDER


def plan_sdk(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    csp = normalize_provider(config.get("csp") or "AWS")
    plan_map, _, _, order = _handlers(csp)
    lines: list[str] = []
    errors: list[str] = []
    flags = _module_flags(csp)
    for mod in order:
        if not config.get(flags[mod]):
            continue
        result = plan_map[mod](config, cloud_env)
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
        "has_changes": bool(lines),
    }


def apply_sdk(
    config: dict,
    cloud_env: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    csp = normalize_provider(config.get("csp") or "AWS")
    _, apply_map, _, order = _handlers(csp)
    flags = _module_flags(csp)
    ctx = SdkDeployContext.from_dict(existing_ctx)
    steps: list[str] = []

    if csp == "Azure":
        from app.provision.sdk_modules.azure_providers import ensure_azure_resource_providers

        provider_result = ensure_azure_resource_providers(config, cloud_env)
        steps.extend(provider_result.get("steps") or [])
        if not provider_result.get("success"):
            return {
                "success": False,
                "output": "\n".join(steps),
                "error": provider_result.get("error"),
                "sdk_context": ctx.to_dict(),
            }

    for mod in order:
        if not config.get(flags[mod]):
            continue
        result = apply_map[mod](config, cloud_env, ctx)
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
    csp = normalize_provider(config.get("csp") or "AWS")
    _, _, destroy_map, _ = _handlers(csp)
    destroy_order = GCP_DESTROY_ORDER if normalize_provider(csp) == "GCP" else AZURE_DESTROY_ORDER
    flags = _module_flags(csp)
    ctx = SdkDeployContext.from_dict(existing_ctx)
    steps: list[str] = []
    for mod in destroy_order:
        if not config.get(flags[mod]):
            continue
        result = destroy_map[mod](config, cloud_env, ctx)
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
