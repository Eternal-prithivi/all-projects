"""Organization rollup, summary filtering, and shared helpers."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from fastapi import HTTPException

from app.dashboard.cost_aggregation import get_cached_user_costs
from app.dashboard.cost_snapshots import get_org_cost_trend
from app.database.mongo_client import get_database

DB = get_database()
ORGS = "organizations"
MEMBERS = "organization_members"
INVITES = "organization_invites"

_summary_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 300


def invalidate_org_cache(org_id: str) -> None:
    _summary_cache.pop(org_id, None)


def get_membership(username: str) -> Optional[Dict[str, Any]]:
    return DB[MEMBERS].find_one({"username": username})


def require_membership(username: str, min_role: Optional[str] = None) -> Dict[str, Any]:
    m = get_membership(username)
    if not m:
        raise HTTPException(status_code=404, detail="You are not in an organization")
    if min_role == "admin" and m.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    if min_role == "owner" and m.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return m


def get_org_doc(org_id: str) -> Optional[Dict[str, Any]]:
    try:
        return DB[ORGS].find_one({"_id": ObjectId(org_id)})
    except Exception:
        return None


def list_org_members(org_id: str) -> List[Dict[str, Any]]:
    return list(DB[MEMBERS].find({"org_id": org_id}))


def _current_month_prefix() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def _rollup_vm_counts(usernames: List[str]) -> Dict[str, int]:
    if not usernames:
        return {}
    cluster = list(
        DB["vm_assignments"].aggregate(
            [
                {"$match": {"user_id": {"$in": usernames}}},
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            ]
        )
    )
    provision = list(
        DB["provision_deployments"].aggregate(
            [
                {"$match": {"user_id": {"$in": usernames}}},
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            ]
        )
    )
    counts = {u: 0 for u in usernames}
    for row in cluster:
        counts[row["_id"]] = counts.get(row["_id"], 0) + int(row["count"])
    for row in provision:
        counts[row["_id"]] = counts.get(row["_id"], 0) + int(row["count"])
    return counts


def _rollup_storage_gb(usernames: List[str]) -> Dict[str, float]:
    if not usernames:
        return {}
    rows = list(
        DB["files"].aggregate(
            [
                {"$match": {"owner_username": {"$in": usernames}}},
                {"$group": {"_id": "$owner_username", "bytes": {"$sum": "$size"}}},
            ]
        )
    )
    out = {u: 0.0 for u in usernames}
    for row in rows:
        out[row["_id"]] = round(float(row.get("bytes", 0)) / (1024**3), 2)
    return out


def _rollup_monthly_spend(usernames: List[str]) -> Dict[str, float]:
    month_prefix = _current_month_prefix()
    out = {u: 0.0 for u in usernames}
    if usernames:
        rows = list(
            DB["dashboard_cost_snapshots"].aggregate(
                [
                    {
                        "$match": {
                            "username": {"$in": usernames},
                            "date": {"$regex": f"^{month_prefix}"},
                        }
                    },
                    {"$group": {"_id": "$username", "total": {"$sum": "$total_usd"}}},
                ]
            )
        )
        for row in rows:
            out[row["_id"]] = round(float(row.get("total", 0)), 2)
    for username in usernames:
        if out[username] <= 0:
            cached = get_cached_user_costs(username)
            out[username] = round(float(cached.get("monthly_costs", 0) or 0), 2)
    return out


def _rollup_plans(usernames: List[str], org_id: Optional[str] = None) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {u: None for u in usernames}
    if org_id:
        from app.organizations.billing import ensure_org_billing_defaults

        org = ensure_org_billing_defaults(org_id)
        org_plan = org.get("plan_id")
        if org_plan:
            return {u: org_plan for u in usernames}
    rows = list(
        DB["subscriptions"].find(
            {"user_id": {"$in": usernames}, "status": {"$in": ["active", "trialing", "migrated_to_org"]}},
            {"user_id": 1, "plan_id": 1, "plan": 1},
        )
    )
    for row in rows:
        uid = row.get("user_id")
        out[uid] = row.get("plan_id") or row.get("plan")
    return out


def _member_stats(username: str, member_row: Dict[str, Any], vm_counts, storage, spend, plans) -> Dict[str, Any]:
    joined = member_row.get("joined_at")
    return {
        "username": username,
        "role": member_row.get("role"),
        "joined_at": joined.isoformat() + "Z" if joined else None,
        "vm_count": vm_counts.get(username, 0),
        "storage_gb": storage.get(username, 0.0),
        "monthly_spend_usd": spend.get(username, 0.0),
        "plan": plans.get(username),
    }


def _budget_fields(org: Dict[str, Any], org_spend: float) -> Dict[str, Any]:
    budget = org.get("monthly_budget_usd")
    threshold = float(org.get("budget_alert_threshold") or 80)
    if not budget or float(budget) <= 0:
        return {
            "monthly_budget_usd": None,
            "budget_used_percent": None,
            "budget_status": None,
            "budget_alert_threshold": threshold,
        }
    budget_f = float(budget)
    used_pct = round((org_spend / budget_f) * 100, 1) if budget_f > 0 else 0
    if used_pct >= 100:
        status = "exceeded"
    elif used_pct >= threshold:
        status = "warning"
    else:
        status = "ok"
    return {
        "monthly_budget_usd": budget_f,
        "budget_used_percent": used_pct,
        "budget_status": status,
        "budget_alert_threshold": threshold,
        "approval_threshold_usd": org.get("approval_threshold_usd"),
    }


def build_org_summary(org_id: str, org: Dict[str, Any], members: List[Dict[str, Any]]) -> Dict[str, Any]:
    usernames = [m["username"] for m in members]
    vm_counts = _rollup_vm_counts(usernames)
    storage = _rollup_storage_gb(usernames)
    spend = _rollup_monthly_spend(usernames)
    plans = _rollup_plans(usernames, org_id)

    member_stats = [
        _member_stats(m["username"], m, vm_counts, storage, spend, plans) for m in members
    ]
    org_totals = {
        "member_count": len(members),
        "total_vms": sum(vm_counts.values()),
        "total_storage_gb": round(sum(storage.values()), 2),
        "monthly_spend_usd": round(sum(spend.values()), 2),
    }
    trend = get_org_cost_trend(usernames, days=7)
    budget = _budget_fields(org, org_totals["monthly_spend_usd"])

    return {
        "organization": {
            "id": org_id,
            "name": org.get("name"),
            "slug": org.get("slug"),
            "owner_username": org.get("owner_username"),
        },
        "org_totals": org_totals,
        "trend": trend,
        "members": member_stats,
        "has_cost_data": trend.get("has_data", False) or org_totals["monthly_spend_usd"] > 0,
        **budget,
    }


def filter_summary_for_role(
    summary: Dict[str, Any], my_role: str, my_username: str
) -> Dict[str, Any]:
    if my_role in ("owner", "admin"):
        summary["can_view_member_spend"] = True
        return summary

    filtered_members = []
    for m in summary.get("members", []):
        if m["username"] == my_username:
            filtered_members.append(m)
        else:
            filtered_members.append(
                {
                    "username": m["username"],
                    "role": m["role"],
                    "joined_at": m.get("joined_at"),
                }
            )
    return {
        **summary,
        "members": filtered_members,
        "can_view_member_spend": False,
    }


def get_org_summary(username: str, *, use_cache: bool = True) -> Dict[str, Any]:
    m = get_membership(username)
    if not m:
        return {"organization": None}

    org_id = m["org_id"]
    now = time.time()
    if use_cache and org_id in _summary_cache:
        cached_at, cached = _summary_cache[org_id]
        if now - cached_at < CACHE_TTL_SECONDS:
            return filter_summary_for_role(cached, m.get("role"), username)

    org = get_org_doc(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    members = list_org_members(org_id)
    full = build_org_summary(org_id, org, members)
    full["my_role"] = m.get("role")
    _summary_cache[org_id] = (now, full)
    return filter_summary_for_role(full, m.get("role"), username)


def update_org_settings(org_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "monthly_budget_usd",
        "budget_alert_threshold",
        "approval_threshold_usd",
    }
    payload = {k: v for k, v in updates.items() if k in allowed}
    if not payload:
        raise HTTPException(status_code=400, detail="No valid settings to update")
    payload["settings_updated_at"] = datetime.utcnow()
    DB[ORGS].update_one({"_id": ObjectId(org_id)}, {"$set": payload})
    invalidate_org_cache(org_id)
    org = get_org_doc(org_id) or {}
    return _budget_fields(org, 0)
