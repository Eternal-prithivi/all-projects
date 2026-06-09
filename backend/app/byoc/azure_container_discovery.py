"""List Azure Blob containers for BYOC wizard."""

from __future__ import annotations

from typing import Any, Dict, List

from azure.storage.blob import BlobServiceClient

from app.byoc.credential_resolver import get_user_cloud_credentials, resolve_azure_credentials


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


def list_azure_containers_for_user(username: str, *, max_results: int = 100) -> Dict[str, Any]:
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
        result["containers"] = containers
        result["count"] = len(containers)
        return result

    if not azure.get("is_byoc"):
        return _platform_azure_response(username)

    return {
        "mode": "platform",
        "containers": [],
        "error": "Azure storage account name and key are required.",
    }
