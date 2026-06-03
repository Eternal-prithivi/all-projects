"""List GCS buckets using service account credentials (BYOC wizard)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.byoc.credential_resolver import resolve_gcp_credentials, get_user_cloud_credentials


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


def list_gcp_buckets_for_user(username: str, *, max_results: int = 100) -> Dict[str, Any]:
    """List buckets using active GCP BYOC or platform SA path."""
    byoc = get_user_cloud_credentials(username, "GCP")
    if byoc:
        creds = byoc.get("credentials") or {}
        sa_json = creds.get("service_account_json") or ""
        if not sa_json:
            return {"mode": "byoc", "buckets": [], "error": "GCP BYOC missing service account JSON."}
        result = list_gcp_buckets_from_json(sa_json, max_results=max_results)
        result["mode"] = "byoc"
        return result

    gcp = resolve_gcp_credentials(username)
    path = gcp.get("service_account_key_path") or ""
    if not path:
        return {
            "mode": "platform",
            "buckets": [],
            "error": "GCP platform credentials not configured.",
        }
    from google.cloud import storage as gcp_storage

    client = gcp_storage.Client.from_service_account_json(path)
    buckets = [
        {"name": b.name, "location": b.location or "", "storage_class": ""}
        for b in client.list_buckets(max_results=max_results)
    ]
    return {
        "mode": "platform",
        "project_id": gcp.get("project_id") or settings_gcp_project(),
        "buckets": buckets,
        "count": len(buckets),
    }


def settings_gcp_project() -> str:
    from app.utils.config import settings

    return settings.GCP_PROJECT_ID or ""
