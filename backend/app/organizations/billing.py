"""Organization seat-based billing."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.organizations import service as org_service
from app.payments.subscription_service import VALID_PLAN_IDS, apply_user_plan_limits

DB = get_database()
ORGS = "organizations"
MEMBERS = "organization_members"
ORG_SUBS = "organization_subscriptions"


def _default_billing_fields(owner_username: str, member_count: int = 1) -> Dict[str, Any]:
    return {
        "billing_owner_username": owner_username,
        "plan_id": "free",
        "seat_count": max(1, member_count),
        "billing_cycle": "monthly",
        "subscription_status": "active",
        "razorpay_subscription_id": None,
        "razorpay_customer_id": None,
        "current_period_start": None,
        "current_period_end": None,
    }


def ensure_org_billing_defaults(org_id: str) -> Dict[str, Any]:
    """Lazy migration: set billing fields on org if missing."""
    org = org_service.get_org_doc(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.get("plan_id"):
        return org

    members = org_service.list_org_members(org_id)
    defaults = _default_billing_fields(
        org.get("owner_username") or "",
        len(members),
    )
    DB[ORGS].update_one({"_id": ObjectId(org_id)}, {"$set": defaults})
    org_service.invalidate_org_cache(org_id)
    return {**org, **defaults}


def count_seats_used(org_id: str) -> int:
    return DB[MEMBERS].count_documents({"org_id": org_id})


def can_manage_billing(username: str, membership: Dict[str, Any]) -> bool:
    role = membership.get("role")
    if role in ("owner", "admin"):
        return True
    org = org_service.get_org_doc(membership["org_id"]) or {}
    return org.get("billing_owner_username") == username


def get_org_limits(org_id: str) -> Dict[str, Any]:
    from app.payments.routes_payments import PLANS

    org = ensure_org_billing_defaults(org_id)
    plan_id = org.get("plan_id") or "free"
    plan = PLANS.get(plan_id) or PLANS["free"]
    seats_used = count_seats_used(org_id)
    seat_count = int(org.get("seat_count") or 1)
    return {
        "plan_id": plan_id,
        "vm_limit": plan.vm_limit,
        "storage_gb": plan.storage_gb,
        "seat_count": seat_count,
        "seats_used": seats_used,
        "seats_available": max(0, seat_count - seats_used),
    }


def org_subscription_to_api(org: Dict[str, Any], membership: Dict[str, Any]) -> Dict[str, Any]:
    from app.payments.routes_payments import PLANS

    org_id = membership.get("org_id")
    plan_id = org.get("plan_id") or "free"
    plan = PLANS.get(plan_id) or PLANS["free"]
    limits = get_org_limits(org_id) if org_id else {}
    return {
        "user_id": membership.get("username"),
        "plan_id": plan_id,
        "plan_name": plan.name,
        "status": org.get("subscription_status", "active"),
        "subscription_id": org.get("razorpay_subscription_id"),
        "razorpay_subscription_id": org.get("razorpay_subscription_id"),
        "razorpay_customer_id": org.get("razorpay_customer_id"),
        "current_period_start": org.get("current_period_start"),
        "current_period_end": org.get("current_period_end"),
        "auto_renew": org.get("subscription_status") != "canceled",
        "billing_cycle": org.get("billing_cycle", "monthly"),
        "vm_limit": plan.vm_limit,
        "storage_gb": plan.storage_gb,
        "managed_by_org": True,
        "org_id": org_id,
        "org_name": org.get("name"),
        "seat_count": limits.get("seat_count", 1),
        "seats_used": limits.get("seats_used", 1),
        "seats_available": limits.get("seats_available", 0),
        "my_role": membership.get("role"),
        "can_manage_billing": can_manage_billing(membership.get("username"), membership),
    }


def get_billing_summary(username: str) -> Dict[str, Any]:
    m = org_service.get_membership(username)
    if not m:
        raise HTTPException(status_code=404, detail="You are not in an organization")
    org = ensure_org_billing_defaults(m["org_id"])
    org["id"] = m["org_id"]
    limits = get_org_limits(m["org_id"])
    sub_api = org_subscription_to_api(org, m)
    return {
        **sub_api,
        **limits,
        "billing_owner_username": org.get("billing_owner_username"),
        "can_manage_billing": can_manage_billing(username, m),
    }


def assert_seats_available(org_id: str) -> None:
    limits = get_org_limits(org_id)
    if limits["seats_used"] >= limits["seat_count"]:
        raise HTTPException(
            status_code=402,
            detail="No seats available. Add seats on Billing before inviting or accepting members.",
        )


def activate_org_subscription(
    org_id: str,
    *,
    plan_id: str,
    seat_count: int,
    billing_cycle: str,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    total_amount: float,
    actor_username: str,
) -> Dict[str, Any]:
    if plan_id not in VALID_PLAN_IDS:
        raise ValueError(f"Invalid plan_id: {plan_id}")

    now = datetime.utcnow()
    period_end = now + timedelta(days=365 if billing_cycle == "yearly" else 30)
    members = org_service.list_org_members(org_id)
    if seat_count < len(members):
        seat_count = len(members)

    org_update = {
        "plan_id": plan_id,
        "seat_count": seat_count,
        "billing_cycle": billing_cycle,
        "subscription_status": "active",
        "razorpay_order_id": razorpay_order_id,
        "current_period_start": now,
        "current_period_end": period_end,
        "billing_updated_at": now,
    }
    DB[ORGS].update_one({"_id": ObjectId(org_id)}, {"$set": org_update})

    DB[ORG_SUBS].update_one(
        {"org_id": org_id},
        {
            "$set": {
                "org_id": org_id,
                "plan_id": plan_id,
                "seat_count": seat_count,
                "billing_cycle": billing_cycle,
                "status": "active",
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "current_period_start": now,
                "current_period_end": period_end,
                "updated_at": now,
                "updated_by": actor_username,
            },
            "$push": {
                "payment_history": {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "amount": total_amount,
                    "plan_id": plan_id,
                    "seat_count": seat_count,
                    "paid_at": now,
                }
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    for member in members:
        apply_user_plan_limits(member["username"], plan_id)
        DB[MEMBERS].update_one(
            {"org_id": org_id, "username": member["username"]},
            {"$set": {"seat_assigned_at": now}},
        )

    org_service.invalidate_org_cache(org_id)
    return get_org_limits(org_id)


def migrate_personal_subscription_to_org(username: str) -> Dict[str, Any]:
    """One-time: copy owner's personal sub to org billing."""
    m = org_service.require_membership(username, min_role="owner")
    org_id = m["org_id"]
    org = ensure_org_billing_defaults(org_id)

    if org.get("plan_id") and org.get("plan_id") != "free" and org.get("current_period_end"):
        raise HTTPException(status_code=400, detail="Organization already has an active paid plan")

    from app.payments.subscription_service import find_subscription_doc

    personal = find_subscription_doc(username)
    if not personal or personal.get("plan_id", "free") == "free":
        raise HTTPException(status_code=400, detail="No paid personal subscription to migrate")

    members = org_service.list_org_members(org_id)
    seat_count = max(int(org.get("seat_count") or 1), len(members))

    DB[ORGS].update_one(
        {"_id": ObjectId(org_id)},
        {
            "$set": {
                "plan_id": personal.get("plan_id"),
                "seat_count": seat_count,
                "billing_cycle": personal.get("billing_cycle", "monthly"),
                "subscription_status": personal.get("status", "active"),
                "razorpay_subscription_id": personal.get("razorpay_subscription_id"),
                "razorpay_customer_id": personal.get("razorpay_customer_id"),
                "current_period_start": personal.get("current_period_start"),
                "current_period_end": personal.get("current_period_end"),
                "billing_owner_username": username,
                "migrated_from_user": username,
                "billing_updated_at": datetime.utcnow(),
            }
        },
    )

    DB["subscriptions"].update_one(
        {"$or": [{"user_id": username}, {"username": username}]},
        {"$set": {"status": "migrated_to_org", "migrated_org_id": org_id, "updated_at": datetime.utcnow()}},
    )

    for member in members:
        apply_user_plan_limits(member["username"], personal.get("plan_id", "free"))

    org_service.invalidate_org_cache(org_id)
    return get_billing_summary(username)


def cancel_org_subscription(username: str) -> Dict[str, Any]:
    m = org_service.require_membership(username, min_role="owner")
    org_id = m["org_id"]
    DB[ORGS].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"subscription_status": "canceled", "auto_renew": False, "billing_updated_at": datetime.utcnow()}},
    )
    org_service.invalidate_org_cache(org_id)
    return {"success": True, "subscription_status": "canceled"}
