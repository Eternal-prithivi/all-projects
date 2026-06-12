"""Per-member BYOC readiness for team admins (no secrets)."""

from __future__ import annotations

from typing import Any, Dict, List

from app.byoc.capabilities import build_byoc_capabilities_payload
from app.byoc.credential_resolver import get_byoc_status
from app.cloud.providers import normalize_provider_key


def _cloud_summary_label(features: Dict[str, bool]) -> str:
    if not any(features.values()):
        return "not connected"
    if all(features.values()):
        return "full"
    if features.get("storage") and features.get("security"):
        locked = [f for f, ok in features.items() if not ok]
        if locked:
            return "storage only"
    return "partial"


def member_cloud_status(username: str) -> Dict[str, Any]:
    """BYOC capability summary for one org member."""
    caps = build_byoc_capabilities_payload(username)
    status = get_byoc_status(username)
    connected: List[str] = []
    summary: Dict[str, str] = {}
    for provider, key in (("AWS", "aws"), ("GCP", "gcp"), ("Azure", "azure")):
        entry = caps.get(key) or {}
        features = entry.get("features") or {}
        if (status.get(key) or {}).get("connected"):
            connected.append(provider)
        summary[provider] = _cloud_summary_label(features)
    return {
        "username": username,
        "byoc_connected": connected,
        "capabilities": caps,
        "cloud_summary": summary,
    }


def org_members_cloud_status(usernames: List[str]) -> List[Dict[str, Any]]:
    return [member_cloud_status(u) for u in usernames]
