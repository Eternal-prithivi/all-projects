"""List Azure Blob containers for BYOC wizard."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from azure.storage.blob import BlobServiceClient

from app.byoc.aws_bucket_discovery import filter_buckets_for_surface
from app.byoc.credential_resolver import (
    get_azure_container_layout,
    get_user_cloud_credentials,
    resolve_azure_credentials,
)


def _azure_layout_for_surface_filter(layout: Optional[dict]) -> Optional[dict]:
    if not layout:
        return None
    return {
        "storage_bucket_name": layout.get("storage_container_name"),
        "secure_bucket_name": layout.get("secure_container_name"),
        "replica_bucket_name": layout.get("replica_container_name"),
        "primary_region": "",
        "replica_region": "",
    }


def _filter_azure_containers_for_surface(
    containers: List[Dict[str, Any]],
    surface: str,
    layout: Optional[dict],
) -> List[Dict[str, Any]]:
    aws_style = [
        {
            "name": c["name"],
            "region": "",
            "role": c.get("role", "storage"),
            "is_default": c.get("is_default", False),
            "is_replica": c.get("is_replica", False),
        }
        for c in containers
    ]
    filtered = filter_buckets_for_surface(
        aws_style,
        "security" if surface == "security" else "storage",
        layout=_azure_layout_for_surface_filter(layout),
    )
    return [
        {
            "name": item["name"],
            "is_default": item.get("is_default", False),
            "is_replica": item.get("is_replica", False),
            "role": item.get("role", "storage"),
        }
        for item in filtered
    ]


def _meter_azure_list_containers(username: str) -> None:
    try:
        from app.billing.storage_metering import record_storage_meter_event

        record_storage_meter_event(username, "Azure", "list_containers", count=1)
    except Exception:
        pass


def _platform_azure_response(username: str) -> Dict[str, Any]:
    from app.cloud.platform_storage_catalog import (
        catalog_is_multi_region,
        default_platform_slug,
        get_platform_buckets_for_csp,
        supported_aws_region_codes,
    )

    azure = resolve_azure_credentials(username)
    containers = get_platform_buckets_for_csp("Azure", surface="storage")
    default_container = (azure.get("container_name") or "").strip()
    for c in containers:
        if c.get("is_default"):
            default_container = c.get("name") or default_container
            break
    account = (azure.get("account_name") or "").strip() or None
    return {
        "mode": "platform",
        "account_name": account,
        "default_container": default_container or None,
        "containers": containers,
        "count": len(containers),
        "platform_multi_region": catalog_is_multi_region(),
        "supported_regions": supported_aws_region_codes() if catalog_is_multi_region() else [],
        "default_platform_slug": default_platform_slug(),
    }


def _blob_client(account_name: str, account_key: str) -> BlobServiceClient:
    conn_str = (
        "DefaultEndpointsProtocol=https;"
        f"AccountName={account_name};"
        f"AccountKey={account_key};"
        "EndpointSuffix=core.windows.net"
    )
    return BlobServiceClient.from_connection_string(conn_str)


def list_azure_containers_from_keys(
    account_name: str,
    account_key: str,
    *,
    max_results: int = 100,
) -> Dict[str, Any]:
    try:
        client = _blob_client(account_name, account_key)
        containers: List[Dict[str, Any]] = []
        for container in client.list_containers():
            containers.append({"name": container["name"]})
            if len(containers) >= max_results:
                break
        return {
            "mode": "discover",
            "account_name": account_name,
            "containers": containers,
            "count": len(containers),
        }
    except Exception as exc:
        return {
            "mode": "discover",
            "containers": [],
            "error": str(exc)[:200],
        }


def list_azure_containers_for_user(
    username: str,
    *,
    surface: str = "storage",
    max_results: int = 100,
) -> Dict[str, Any]:
    azure = resolve_azure_credentials(username)
    default_container = (azure.get("container_name") or "").strip()
    byoc = get_user_cloud_credentials(username, "Azure")

    if byoc:
        account = (azure.get("account_name") or "").strip()
        key = (azure.get("account_key") or "").strip()
        if not account or not key:
            return {
                "mode": "byoc",
                "containers": [],
                "error": "Azure storage account name and key are required.",
            }
        result = list_azure_containers_from_keys(account, key, max_results=max_results)
        _meter_azure_list_containers(username)
        layout = get_azure_container_layout(username)
        if surface == "security" and layout:
            default_container = layout.get("secure_container_name") or default_container
        containers = []
        for item in result.get("containers") or []:
            entry = dict(item)
            entry["is_default"] = bool(
                default_container and entry.get("name") == default_container
            )
            containers.append(entry)
        if default_container and not any(c.get("is_default") for c in containers):
            containers.insert(0, {"name": default_container, "is_default": True})
        result["mode"] = "byoc"
        result["account_name"] = account
        result["default_container"] = default_container or None
        result["containers"] = _filter_azure_containers_for_surface(
            containers, surface, layout
        )
        result["surface"] = surface
        result["count"] = len(result["containers"])
        return result

    if not azure.get("is_byoc"):
        return _platform_azure_response(username)

    return {
        "mode": "platform",
        "containers": [],
        "error": "Azure storage account name and key are required.",
    }
