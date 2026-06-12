"""Plan feature entitlements and quota helpers — single source of truth for gating."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.payments.subscription_service import VALID_PLAN_IDS, get_effective_plan_id

FEATURE_MIN_PLAN: Dict[str, str] = {
    "live_billing": "basic",
    "byoc": "pro",
    "provision_policies": "pro",
    "api_access": "pro",
    "team_seat_billing": "pro",
    "ai_recommendations": "pro",
}

PLAN_ORDER = ("free", "basic", "pro", "enterprise")


def _plan_rank(plan_id: str) -> int:
    try:
        return PLAN_ORDER.index(plan_id)
    except ValueError:
        return 0


def _features_for_plan(plan_id: str) -> Dict[str, bool]:
    rank = _plan_rank(plan_id)
    return {key: rank >= _plan_rank(min_plan) for key, min_plan in FEATURE_MIN_PLAN.items()}


def _nav_entitlements(features: Dict[str, bool]) -> List[Dict[str, Any]]:
    entries = [
        ("overview", False, None),
        ("storage", False, None),
        ("vmcluster", False, None),
        ("security", False, None),
        ("provision", False, None),
        ("provision_policies", not features["provision_policies"], "pro"),
        ("costs", False, None),
        ("cost_optimization", not features["ai_recommendations"], "pro"),
        ("cost_simulator", not features["ai_recommendations"], "pro"),
        ("team", False, None),
        ("team_seat_billing", not features["team_seat_billing"], "pro"),
        ("billing", False, None),
        ("support", False, None),
        ("byoc", not features["byoc"], "pro"),
        ("api_access", not features["api_access"], "pro"),
    ]
    return [
        {
            "id": nav_id,
            "locked": locked,
            **({"min_plan": min_plan} if min_plan else {}),
        }
        for nav_id, locked, min_plan in entries
    ]


def feature_upgrade_detail(feature_key: str) -> Dict[str, str]:
    min_plan = FEATURE_MIN_PLAN.get(feature_key, "pro")
    labels = {"free": "Free", "basic": "Basic", "pro": "Pro", "enterprise": "Enterprise"}
    return {
        "feature": feature_key,
        "min_plan": min_plan,
        "min_plan_name": labels.get(min_plan, min_plan.title()),
    }


def require_feature(username: str, feature_key: str) -> None:
    """Raise HTTP 403 when the user's plan lacks a feature."""
    plan_id = get_effective_plan_id(username)
    features = _features_for_plan(plan_id)
    if features.get(feature_key):
        return
    meta = feature_upgrade_detail(feature_key)
    raise HTTPException(
        status_code=403,
        detail={
            "code": "plan_feature_locked",
            "message": f"This feature requires the {meta['min_plan_name']} plan or above.",
            "feature": feature_key,
            "current_plan": plan_id,
            "min_plan": meta["min_plan"],
            "upgrade_required": True,
        },
    )


def get_entitlements(username: str) -> Dict[str, Any]:
    """Full entitlements payload for API and UI."""
    from app.payments.routes_payments import PLANS
    from app.payments.quota_service import get_usage_snapshot

    plan_id = get_effective_plan_id(username)
    plan = PLANS.get(plan_id) or PLANS["free"]
    features = _features_for_plan(plan_id)
    usage = get_usage_snapshot(username)

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "limits": {
            "vm_limit": plan.vm_limit,
            "storage_gb": plan.storage_gb,
            **usage,
        },
        "features": features,
        "nav": _nav_entitlements(features),
    }


def is_feature_enabled(username: str, feature_key: str) -> bool:
    plan_id = get_effective_plan_id(username)
    return _features_for_plan(plan_id).get(feature_key, False)
