"""Personal and organization VM/storage quota enforcement."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.organizations.resource_acl import get_org_context

DB = get_database()

_ACTIVE_VM_STATUSES = {"$nin": ["destroyed", "archived", "released", "terminated"]}


def count_org_vms(org_id: str) -> int:
    cluster = DB["vm_assignments"].count_documents(
        {"org_id": org_id, "status": {"$in": ["assigned", "active"]}}
    )
    provisioned = DB["provision_deployments"].count_documents(
        {"org_id": org_id, "status": _ACTIVE_VM_STATUSES}
    )
    return cluster + provisioned


def count_org_storage_bytes(org_id: str) -> int:
    rows = list(
        DB["files"].aggregate(
            [{"$match": {"org_id": org_id}}, {"$group": {"_id": None, "total": {"$sum": "$size"}}}]
        )
    )
    return int(rows[0]["total"]) if rows else 0


def count_personal_vms(username: str) -> int:
    solo_filter = {
        "$or": [
            {"org_id": {"$exists": False}},
            {"org_id": None},
        ]
    }
    cluster = DB["vm_assignments"].count_documents(
        {
            **solo_filter,
            "user_id": username,
            "status": {"$in": ["assigned", "active"]},
        }
    )
    provisioned = DB["provision_deployments"].count_documents(
        {
            **solo_filter,
            "user_id": username,
            "status": _ACTIVE_VM_STATUSES,
        }
    )
    return cluster + provisioned


def count_personal_storage_bytes(username: str) -> int:
    rows = list(
        DB["files"].aggregate(
            [
                {
                    "$match": {
                        "$or": [
                            {"org_id": {"$exists": False}},
                            {"org_id": None},
                        ],
                        "owner_username": username,
                    }
                },
                {"$group": {"_id": None, "total": {"$sum": "$size"}}},
            ]
        )
    )
    return int(rows[0]["total"]) if rows else 0


def _limits_for_user(username: str) -> Dict[str, Any]:
    from app.billing.csp_free_tier import (
        FREE_PLAN_STORAGE_GB,
        FREE_PLAN_VM_LIMIT,
        is_free_platform_plan,
    )
    from app.organizations.billing import get_org_limits
    from app.payments.routes_payments import PLANS
    from app.payments.subscription_service import get_effective_plan_id

    ctx = get_org_context(username)
    if ctx:
        return get_org_limits(ctx["org_id"])
    plan_id = get_effective_plan_id(username)
    if is_free_platform_plan(plan_id):
        return {"vm_limit": FREE_PLAN_VM_LIMIT, "storage_gb": FREE_PLAN_STORAGE_GB}
    plan = PLANS.get(plan_id) or PLANS["free"]
    return {"vm_limit": plan.vm_limit, "storage_gb": plan.storage_gb}


def get_usage_snapshot(username: str) -> Dict[str, int]:
    ctx = get_org_context(username)
    if ctx:
        return {
            "vms_used": count_org_vms(ctx["org_id"]),
            "storage_bytes_used": count_org_storage_bytes(ctx["org_id"]),
        }
    return {
        "vms_used": count_personal_vms(username),
        "storage_bytes_used": count_personal_storage_bytes(username),
    }


def assert_vm_quota(username: str) -> None:
    limits = _limits_for_user(username)
    ctx = get_org_context(username)
    current = count_org_vms(ctx["org_id"]) if ctx else count_personal_vms(username)
    cap = int(limits.get("vm_limit", 2))
    if cap < 999 and current >= cap:
        scope = "Organization" if ctx else "Plan"
        raise HTTPException(
            status_code=403,
            detail={
                "code": "vm_quota_exceeded",
                "message": f"{scope} VM limit reached ({current}/{cap}). Upgrade plan or remove resources.",
                "current": current,
                "cap": cap,
                "upgrade_required": True,
            },
        )


def assert_storage_quota(username: str, additional_bytes: int = 0) -> None:
    limits = _limits_for_user(username)
    ctx = get_org_context(username)
    cap_gb = float(limits.get("storage_gb", 10))
    cap_bytes = int(cap_gb * (1024**3))
    current = (
        count_org_storage_bytes(ctx["org_id"])
        if ctx
        else count_personal_storage_bytes(username)
    )
    if current + additional_bytes > cap_bytes:
        scope = "Organization" if ctx else "Plan"
        raise HTTPException(
            status_code=403,
            detail={
                "code": "storage_quota_exceeded",
                "message": f"{scope} storage limit exceeded ({cap_gb} GB cap).",
                "upgrade_required": True,
            },
        )


def maybe_assert_quotas(username: str, *, storage_bytes: int = 0) -> None:
    """Assert VM quota always; storage when uploading."""
    assert_vm_quota(username)
    if storage_bytes > 0:
        assert_storage_quota(username, storage_bytes)
