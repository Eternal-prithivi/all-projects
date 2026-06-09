"""List GCS buckets using service account credentials (BYOC wizard)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.byoc.credential_resolver import resolve_gcp_credentials, get_user_cloud_credentials


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
    buckets = get_platform_buckets_for_csp("GCP", surface="storage")
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


def list_gcp_buckets_for_user(username: str, *, max_results: int = 100) -> Dict[str, Any]:
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
        result["default_bucket"] = default_bucket or None
        result["buckets"] = _mark_default_gcp_bucket(result.get("buckets") or [], default_bucket)
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
