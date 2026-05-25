"""Audit log helpers — categorization, deduplication, and query utilities."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def categorize_audit_action(action: str) -> str:
    """Map free-text action to a filter category."""
    a = (action or "").lower()
    if any(k in a for k in ("login", "session", "sign-in", "sign in")):
        return "auth"
    if any(k in a for k in ("password", "2fa", "security alert", "encrypt")):
        return "security"
    if any(k in a for k in ("profile", "account", "api key", "billing")):
        return "account"
    return "other"


def dedupe_audit_entries(entries: List[Dict[str, Any]], window_minutes: int = 30) -> List[Dict[str, Any]]:
    """
    Collapse repeated identical events within a time window.
    Keeps the newest entry and appends a repeat count to the description when collapsed.
    """
    if not entries:
        return []

    sorted_entries = sorted(
        entries,
        key=lambda e: e.get("timestamp") or datetime.min,
        reverse=True,
    )

    deduped: List[Dict[str, Any]] = []
    for entry in sorted_entries:
        action = entry.get("action", "")
        ts = entry.get("timestamp")
        if not isinstance(ts, datetime):
            deduped.append(entry)
            continue

        merged = False
        for kept in deduped:
            if kept.get("action") != action:
                continue
            kept_ts = kept.get("timestamp")
            if not isinstance(kept_ts, datetime):
                continue
            if abs((kept_ts - ts).total_seconds()) <= window_minutes * 60:
                count = kept.get("_repeat_count", 1) + 1
                kept["_repeat_count"] = count
                base_desc = kept.get("description", "").split(" (")[0]
                kept["description"] = f"{base_desc} ({count} similar events)"
                merged = True
                break

        if not merged:
            clean = dict(entry)
            clean["_repeat_count"] = 1
            deduped.append(clean)

    return deduped


def build_activity_query(
    username: str,
    *,
    days: int = 30,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """MongoDB query for user activity within a retention window."""
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))
    query: Dict[str, Any] = {
        "username": username,
        "timestamp": {"$gte": since},
    }
    return query


def filter_by_category(entries: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    if not category or category == "all":
        return entries
    return [e for e in entries if categorize_audit_action(e.get("action", "")) == category]
