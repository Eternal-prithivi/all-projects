"""List Azure Blob containers for BYOC wizard."""

from __future__ import annotations

from typing import Any, Dict, List

from azure.storage.blob import BlobServiceClient

from app.byoc.credential_resolver import get_user_cloud_credentials, resolve_azure_credentials


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
    account = (azure.get("account_name") or "").strip()
    key = (azure.get("account_key") or "").strip()
    if not account or not key:
        return {
            "mode": "byoc" if azure.get("is_byoc") else "platform",
            "containers": [],
            "error": "Azure storage account name and key are required.",
        }
    result = list_azure_containers_from_keys(account, key, max_results=max_results)
    result["mode"] = "byoc" if azure.get("is_byoc") else "platform"
    return result
