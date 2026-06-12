"""Expose provisioned storage (S3 / GCS / Blob) on the Storage page bucket lists."""

from __future__ import annotations

from typing import Any, Optional

from app.cloud.providers import normalize_provider
from app.provision.models import DeploymentStatus


def _storage_enabled(config: dict[str, Any]) -> bool:
    return bool(
        config.get("enable_s3")
        or config.get("enable_gcs")
        or config.get("enable_azure_storage")
    )


def _bucket_entry_from_config(
    config: dict[str, Any],
    deployment_id: str,
    created_resources: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Build a Storage UI bucket/container dict from deployment config + created_resources."""
    csp = normalize_provider(config.get("csp") or "AWS")
    label = (config.get("deployment_display_name") or deployment_id).strip()
    base = {
        "provisioned": True,
        "deployment_id": deployment_id,
        "provisioned_label": label,
        "role": "storage",
        "is_default": False,
        "is_replica": False,
    }

    bucket_res = next((r for r in created_resources if r.get("type") == "bucket"), None)

    if csp == "AWS" and config.get("enable_s3"):
        name = (bucket_res or {}).get("name") or config.get("bucket_name") or ""
        name = str(name).strip()
        if not name:
            return None
        return {
            **base,
            "name": name,
            "region": config.get("aws_region") or "",
        }

    if csp == "GCP" and config.get("enable_gcs"):
        name = (bucket_res or {}).get("name") or config.get("bucket_name") or ""
        name = str(name).strip()
        if not name:
            return None
        loc = config.get("gcp_region") or ""
        return {
            **base,
            "name": name,
            "location": loc,
            "region": loc,
        }

    if csp == "Azure" and config.get("enable_azure_storage"):
        container = (
            (bucket_res or {}).get("name")
            or config.get("container_name")
            or "zenith-static"
        )
        account = (
            (bucket_res or {}).get("account_name")
            or (bucket_res or {}).get("id")
            or config.get("storage_account_name")
            or ""
        )
        container = str(container).strip()
        account = str(account).strip()
        if not container:
            return None
        return {
            **base,
            "name": container,
            "account_name": account,
            "region": config.get("azure_location") or "",
        }

    return None


def list_provisioned_storage_buckets(username: str, csp: str) -> list[dict[str, Any]]:
    """Active deployed stacks with storage modules → bucket selector entries."""
    from app.database.mongo_client import get_database

    provider = normalize_provider(csp)
    collection = get_database()["provision_deployments"]
    cursor = collection.find(
        {
            "user_id": username,
            "status": DeploymentStatus.DEPLOYED.value,
            "$or": [
                {"csp": provider},
                {"config.csp": provider},
            ],
        },
        {
            "deployment_name": 1,
            "config": 1,
            "created_resources": 1,
        },
    )

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in cursor:
        config = doc.get("config") or {}
        if not _storage_enabled(config):
            continue
        entry = _bucket_entry_from_config(
            config,
            doc.get("deployment_name", ""),
            doc.get("created_resources") or [],
        )
        if not entry:
            continue
        dedupe_key = f"{entry.get('account_name', '')}:{entry['name']}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        out.append(entry)
    return out


def merge_provisioned_storage_buckets(
    username: str,
    csp: str,
    buckets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Append provisioned targets; skip names already in the catalog/discovery list."""
    provisioned = list_provisioned_storage_buckets(username, csp)
    if not provisioned:
        return buckets

    existing: set[str] = set()
    for b in buckets:
        name = (b.get("name") or "").strip()
        account = (b.get("account_name") or "").strip()
        existing.add(f"{account}:{name}" if account else name)

    merged = list(buckets)
    for entry in provisioned:
        name = entry["name"]
        account = (entry.get("account_name") or "").strip()
        key = f"{account}:{name}" if account else name
        if key in existing:
            continue
        merged.append(entry)
        existing.add(key)
    return merged
