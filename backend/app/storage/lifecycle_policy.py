"""Lifecycle policy constants, defaults, and user preference helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional, Tuple

from app.database.mongo_client import get_database

LifecyclePolicy = Literal["auto", "keep_hot", "aggressive", "manual"]
LifecycleAction = Literal["keep_hot", "snooze", "approve"]

VALID_POLICIES = ("auto", "keep_hot", "aggressive", "manual")
DEFAULT_POLICY: LifecyclePolicy = "auto"
DEFAULT_NOTICE_DAYS = 7
SNOOZE_DAYS_DEFAULT = 30

POLICY_LABELS = {
    "auto": "Auto-optimize (recommended)",
    "keep_hot": "Keep fast access",
    "aggressive": "Archive aggressively",
    "manual": "Suggest only — no automatic moves",
}

# Demotion inactivity thresholds (days) per policy
DEMOTION_THRESHOLDS: Dict[str, Tuple[int, int]] = {
    "auto": (30, 90),       # hot→warm, warm→cold
    "aggressive": (14, 60),
    "keep_hot": (99999, 99999),
    "manual": (99999, 99999),
}


def suggest_lifecycle_policy(user_priority: str, user_intent: str) -> LifecyclePolicy:
    """Map upload-time priority/intent to a sensible default lifecycle policy."""
    priority = (user_priority or "balanced").lower()
    intent = (user_intent or "active").lower()
    if intent in ("frequent",) or priority == "performance":
        return "keep_hot"
    if intent == "archival" and priority == "cost":
        return "aggressive"
    if intent == "archival":
        return "auto"
    if intent == "infrequent" and priority == "cost":
        return "aggressive"
    return "auto"


def normalize_lifecycle_policy(value: Optional[str], fallback: str = DEFAULT_POLICY) -> str:
    policy = (value or fallback or DEFAULT_POLICY).lower().strip()
    return policy if policy in VALID_POLICIES else fallback


def get_user_lifecycle_preferences(username: str) -> Dict[str, Any]:
    """Account defaults from users.settings.preferences."""
    user = get_database()["users"].find_one({"username": username}) or {}
    prefs = (user.get("settings") or {}).get("preferences") or {}
    return {
        "default_lifecycle_policy": normalize_lifecycle_policy(
            prefs.get("default_lifecycle_policy"),
            DEFAULT_POLICY,
        ),
        "lifecycle_notice_days": max(
            0,
            min(int(prefs.get("lifecycle_notice_days", DEFAULT_NOTICE_DAYS)), 30),
        ),
    }


def demotion_thresholds(policy: str) -> Tuple[int, int]:
    return DEMOTION_THRESHOLDS.get(normalize_lifecycle_policy(policy), DEMOTION_THRESHOLDS["auto"])


def policy_allows_demotion(policy: str) -> bool:
    return normalize_lifecycle_policy(policy) in ("auto", "aggressive")


def as_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_snoozed(file_record: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    until = as_utc(file_record.get("lifecycle_snoozed_until"))
    return bool(until and until > now)


def resolve_upload_lifecycle_policy(
    username: str,
    *,
    explicit: Optional[str],
    user_priority: Optional[str] = None,
    user_intent: Optional[str] = None,
) -> str:
    if explicit:
        return normalize_lifecycle_policy(explicit)
    defaults = get_user_lifecycle_preferences(username)
    account_default = defaults["default_lifecycle_policy"]
    if account_default != DEFAULT_POLICY:
        return account_default
    if user_priority or user_intent:
        return suggest_lifecycle_policy(user_priority or "balanced", user_intent or "active")
    return DEFAULT_POLICY


def build_pending_demotion(
    *,
    target_tier: str,
    priority: Dict[str, Any],
    notice_days: int,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    execute_after = now + timedelta(days=max(notice_days, 0))
    savings = (priority.get("factors") or {}).get("estimated_monthly_savings", 0)
    return {
        "target_tier": target_tier,
        "proposed_at": now,
        "execute_after": execute_after,
        "estimated_monthly_savings": savings,
        "priority": priority,
    }


def pending_is_due(pending: Optional[Dict[str, Any]], now: Optional[datetime] = None) -> bool:
    if not pending:
        return False
    now = now or datetime.now(timezone.utc)
    execute_after = as_utc(pending.get("execute_after"))
    return bool(execute_after and execute_after <= now)
