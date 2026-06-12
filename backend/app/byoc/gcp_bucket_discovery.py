"""List GCS buckets using service account credentials (BYOC wizard)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional  # noqa: F401 used in helpers

from app.byoc.aws_bucket_discovery import filter_buckets_for_surface
from app.byoc.credential_resolver import (
    get_gcp_bucket_layout,
    get_user_cloud_credentials,
    resolve_gcp_credentials,
)


def _gcp_layout_for_surface_filter(layout: Optional[dict]) -> Optional[dict]:
    if not layout:
        return None
    return {
        "storage_bucket_name": layout.get("storage_bucket_name"),
        "secure_bucket_name": layout.get("secure_bucket_name"),
        "replica_bucket_name": layout.get("replica_bucket_name"),
        "primary_region": layout.get("primary_location"),
        "replica_region": layout.get("replica_location"),
    }


def _filter_gcp_buckets_for_surface(
    buckets: List[Dict[str, Any]],
    surface: str,
    layout: Optional[dict],
) -> List[Dict[str, Any]]:
    aws_style = [
        {
            "name": b["name"],
            "region": b.get("location") or b.get("region") or "",
            "role": b.get("role", "storage"),
            "is_default": b.get("is_default", False),
            "is_replica": b.get("is_replica", False),
        }
        for b in buckets
    ]
    filtered = filter_buckets_for_surface(
        aws_style,
        "security" if surface == "security" else "storage",
        layout=_gcp_layout_for_surface_filter(layout),
    )
    out: List[Dict[str, Any]] = []
    for item in filtered:
        original = next((b for b in buckets if b["name"] == item["name"]), {})
        out.append(
            {
                "name": item["name"],
                "location": original.get("location") or item.get("region") or "",
                "storage_class": original.get("storage_class", ""),
                "is_default": item.get("is_default", False),
                "is_replica": item.get("is_replica", False),
                "role": item.get("role", "storage"),
            }
        )
    return out


def _meter_gcp_list_buckets(username: str) -> None:
    try:
        from app.billing.storage_metering import record_storage_meter_event

        record_storage_meter_event(username, "GCP", "list_buckets", count=1)
    except Exception:
        pass


def _platform_gcp_response(username: str) -> Dict[str, Any]:
    from app.cloud.platform_storage_catalog import (
        catalog_is_multi_region,
        default_platform_slug,
        get_platform_buckets_for_csp,
        supported_aws_region_codes,
    )

    gcp = resolve_gcp_credentials(username)
    from app.provision.storage_bridge import merge_provisioned_storage_buckets

    buckets = merge_provisioned_storage_buckets(
        username, "GCP", get_platform_buckets_for_csp("GCP", surface="storage")
    )
    default_bucket = default_platform_slug()
    default_name = (gcp.get("bucket_name") or "").strip()
    for b in buckets:
        if b.get("is_default"):
            default_name = b.get("name") or default_name
            break
    return {
        "mode": "platform",
        "project_id": gcp.get("project_id") or settings_gcp_project(),
        "default_bucket": default_name or None,
        "buckets": buckets,
        "count": len(buckets),
        "platform_multi_region": catalog_is_multi_region(),
        "supported_regions": supported_aws_region_codes() if catalog_is_multi_region() else [],
        "default_platform_slug": default_platform_slug(),
    }


def _client_from_sa_json(service_account_json: str):
    from google.cloud import storage as gcp_storage
    from google.oauth2 import service_account

    raw = service_account_json.strip()
    info = json.loads(raw) if raw.startswith("{") else json.loads(raw)
    credentials = service_account.Credentials.from_service_account_info(info)
    project = info.get("project_id")
    return gcp_storage.Client(credentials=credentials, project=project), project


def list_gcp_buckets_from_json(service_account_json: str, *, max_results: int = 100) -> Dict[str, Any]:
    """List buckets visible to the given service account JSON."""
    try:
        client, project_id = _client_from_sa_json(service_account_json)
        buckets: List[Dict[str, Any]] = []
        for bucket in client.list_buckets(max_results=max_results):
            buckets.append(
                {
                    "name": bucket.name,
                    "location": bucket.location or "",
                    "storage_class": getattr(bucket, "storage_class", None) or "",
                }
            )
        return {
            "mode": "discover",
            "project_id": project_id,
            "buckets": buckets,
            "count": len(buckets),
        }
    except json.JSONDecodeError as exc:
        return {"mode": "discover", "buckets": [], "error": f"Invalid JSON: {exc}"}
    except Exception as exc:
        return {"mode": "discover", "buckets": [], "error": str(exc)[:200]}


def _mark_default_gcp_bucket(
    buckets: List[Dict[str, Any]], default_name: str
) -> List[Dict[str, Any]]:
    default = (default_name or "").strip()
    marked: List[Dict[str, Any]] = []
    for entry in buckets:
        item = dict(entry)
        item["is_default"] = bool(default and item.get("name") == default)
        marked.append(item)
    return marked


def list_gcp_buckets_for_user(
    username: str,
    *,
    surface: str = "storage",
    max_results: int = 100,
) -> Dict[str, Any]:
    """List buckets using active GCP BYOC or platform catalog (no live list for platform)."""
    gcp = resolve_gcp_credentials(username)
    default_bucket = (gcp.get("bucket_name") or "").strip()
    byoc = get_user_cloud_credentials(username, "GCP")
    if byoc:
        creds = byoc.get("credentials") or {}
        sa_json = creds.get("service_account_json") or ""
        if not sa_json:
            return {"mode": "byoc", "buckets": [], "error": "GCP BYOC missing service account JSON."}
        result = list_gcp_buckets_from_json(sa_json, max_results=max_results)
        result["mode"] = "byoc"
        layout = get_gcp_bucket_layout(username)
        if surface == "security" and layout:
            default_bucket = layout.get("secure_bucket_name") or default_bucket
        marked = _mark_default_gcp_bucket(result.get("buckets") or [], default_bucket)
        result["default_bucket"] = default_bucket or None
        from app.provision.storage_bridge import merge_provisioned_storage_buckets

        result["buckets"] = merge_provisioned_storage_buckets(
            username,
            "GCP",
            _filter_gcp_buckets_for_surface(marked, surface, layout),
        )
        result["surface"] = surface
        _meter_gcp_list_buckets(username)
        return result

    if not gcp.get("is_byoc"):
        return _platform_gcp_response(username)

    return {
        "mode": "platform",
        "buckets": [],
        "error": "GCP platform credentials not configured.",
    }


def settings_gcp_project() -> str:
    from app.utils.config import settings

    return settings.GCP_PROJECT_ID or ""
