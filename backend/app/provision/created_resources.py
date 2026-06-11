"""Extract created resource summaries from apply context for handoff."""

from __future__ import annotations

from typing import Any, List

from app.cloud.providers import normalize_provider


def resources_from_boto3_context(config: dict[str, Any], ctx: dict[str, str]) -> List[dict[str, Any]]:
    csp = normalize_provider(config.get("csp") or "AWS")
    out: List[dict[str, Any]] = []
    if ctx.get("instance_id"):
        out.append({
            "type": "vm",
            "name": config.get("instance_name") or ctx["instance_id"],
            "id": ctx["instance_id"],
            "ip": ctx.get("public_ip"),
            "csp": csp,
        })
    if ctx.get("bucket_name"):
        out.append({
            "type": "bucket",
            "name": ctx["bucket_name"],
            "id": ctx["bucket_name"],
            "csp": csp,
        })
    if ctx.get("dynamodb_table"):
        out.append({
            "type": "database",
            "name": ctx["dynamodb_table"],
            "id": ctx["dynamodb_table"],
            "csp": csp,
        })
    return out


def resources_from_sdk_context(config: dict[str, Any], ctx: dict[str, Any]) -> List[dict[str, Any]]:
    csp = normalize_provider(config.get("csp") or "AWS")
    out: List[dict[str, Any]] = []
    if not ctx:
        return out

    vm_id = ctx.get("vm_name") or ctx.get("gce_name") or config.get("instance_name")
    vm_ip = ctx.get("vm_public_ip") or ctx.get("public_ip") or ctx.get("external_ip")
    if vm_id or config.get("enable_gce") or config.get("enable_azure_vm"):
        out.append({
            "type": "vm",
            "name": vm_id or config.get("instance_name", "vm"),
            "id": vm_id or "",
            "ip": vm_ip,
            "csp": csp,
        })
    bucket = ctx.get("gcs_bucket") or ctx.get("azure_storage_account") or ctx.get("bucket_name")
    if bucket or config.get("enable_gcs") or config.get("enable_azure_storage"):
        out.append({
            "type": "bucket",
            "name": bucket or config.get("bucket_name") or config.get("storage_account_name", "storage"),
            "id": bucket or "",
            "csp": csp,
        })
    db = ctx.get("firestore_database_id") or ctx.get("cosmos_database_name")
    if db or config.get("enable_firestore") or config.get("enable_cosmos"):
        out.append({
            "type": "database",
            "name": db or config.get("cosmos_database_name", "database"),
            "id": db or "",
            "csp": csp,
        })
    return out


def resources_from_terraform_state(
    config: dict[str, Any],
    state_resource_names: list[str],
) -> List[dict[str, Any]]:
    """Map terraform.tfstate managed resource names to handoff summaries."""
    csp = normalize_provider(config.get("csp") or "AWS")
    out: List[dict[str, Any]] = []
    for name in state_resource_names:
        lower = name.lower()
        if any(k in lower for k in ("aws_instance", "google_compute_instance", "azurerm_linux_virtual_machine", "azurerm_windows_virtual_machine")):
            out.append({"type": "vm", "name": name, "id": name, "ip": None, "csp": csp})
        elif any(k in lower for k in ("aws_s3_bucket", "google_storage_bucket", "azurerm_storage")):
            out.append({"type": "bucket", "name": name, "id": name, "csp": csp})
        elif any(k in lower for k in ("aws_dynamodb", "google_firestore", "azurerm_cosmosdb")):
            out.append({"type": "database", "name": name, "id": name, "csp": csp})
    return out
