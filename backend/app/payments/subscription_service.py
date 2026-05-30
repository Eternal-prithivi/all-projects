"""
Single source of truth for Zenith subscription plans (MongoDB + optional owner override).

Subscriptions are stored in the ``subscriptions`` collection with both ``user_id`` and
``username`` set to the account username so local dev and production stay consistent.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.database.mongo_client import get_database
from app.utils.config import settings

VALID_PLAN_IDS = frozenset({"free", "basic", "pro", "enterprise"})


def _owner_usernames() -> set[str]:
    raw = getattr(settings, "PLATFORM_OWNER_USERNAMES", "") or ""
    return {u.strip() for u in raw.split(",") if u.strip()}


def _owner_plan_id() -> str:
    plan = (getattr(settings, "PLATFORM_OWNER_PLAN", None) or "enterprise").strip().lower()
    return plan if plan in VALID_PLAN_IDS else "enterprise"


def find_subscription_doc(username: str) -> Optional[dict[str, Any]]:
    """Find subscription by user_id or username (legacy docs may use either)."""
    return get_database()["subscriptions"].find_one(
        {"$or": [{"user_id": username}, {"username": username}]}
    )


def apply_user_plan_limits(username: str, plan_id: str) -> None:
    """Sync VM/storage limits on the user document from plan catalog."""
    from app.payments.routes_payments import PLANS

    plan = PLANS.get(plan_id) or PLANS["free"]
    get_database()["users"].update_one(
        {"username": username},
        {
            "$set": {
                "vm_limit": plan.vm_limit,
                "storage_limit_gb": plan.storage_gb,
                "plan_id": plan_id,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def set_user_subscription(
    username: str,
    plan_id: str,
    *,
    status: str = "active",
    persist: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Upsert subscription and sync user limits."""
    if plan_id not in VALID_PLAN_IDS:
        raise ValueError(f"Invalid plan_id: {plan_id}")

    now = datetime.utcnow()
    payload: dict[str, Any] = {
        "user_id": username,
        "username": username,
        "plan_id": plan_id,
        "status": status,
        "updated_at": now,
        **extra,
    }

    if persist:
        get_database()["subscriptions"].update_one(
            {"$or": [{"user_id": username}, {"username": username}]},
            {"$set": payload, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        apply_user_plan_limits(username, plan_id)

    return payload


def get_effective_plan_id(username: str) -> str:
    """
    Resolve plan for feature gating and UI.

    Priority:
    1. PLATFORM_OWNER_USERNAMES + PLATFORM_OWNER_PLAN (production single-tenant)
    2. subscriptions collection
    3. users.plan_id (legacy local upgrades)
    4. free
    """
    if username in _owner_usernames():
        plan_id = _owner_plan_id()
        set_user_subscription(username, plan_id)
        return plan_id

    sub = find_subscription_doc(username)
    if sub and sub.get("plan_id"):
        plan_id = sub["plan_id"]
        if plan_id in VALID_PLAN_IDS:
            apply_user_plan_limits(username, plan_id)
            return plan_id

    user = get_database()["users"].find_one({"username": username})
    legacy_plan = (user or {}).get("plan_id")
    if legacy_plan and legacy_plan in VALID_PLAN_IDS and legacy_plan != "free":
        set_user_subscription(username, legacy_plan)
        return legacy_plan

    return "free"


def get_user_subscription(username: str) -> dict[str, Any]:
    """Return subscription-shaped dict for API responses."""
    plan_id = get_effective_plan_id(username)
    sub = find_subscription_doc(username) or {}

    return {
        "user_id": username,
        "plan_id": plan_id,
        "status": sub.get("status", "active"),
        "subscription_id": sub.get("subscription_id"),
        "razorpay_subscription_id": sub.get("razorpay_subscription_id"),
        "razorpay_customer_id": sub.get("razorpay_customer_id"),
        "current_period_start": sub.get("current_period_start"),
        "current_period_end": sub.get("current_period_end"),
        "auto_renew": sub.get("auto_renew", True),
        "billing_cycle": sub.get("billing_cycle"),
    }
