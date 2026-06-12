"""Organization billing API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.auth_utils import get_current_user
from app.organizations import billing, service
from app.organizations.billing import activate_org_subscription, cancel_org_subscription
from app.payments.checkout import (
    calculate_order_amount,
    complete_paid_order,
    create_razorpay_order_record,
    verify_razorpay_signature,
)
from app.payments.routes_payments import PLANS
from app.users.user_model import UserInDB

router = APIRouter(prefix="/billing", tags=["Organization Billing"])


class OrgCheckoutBody(BaseModel):
    plan_id: str
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    seat_count: int = Field(default=1, ge=1, le=500)
    cloud_costs_usd: float = Field(default=0.0, ge=0)


class OrgVerifyPaymentBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class OrgSeatsBody(BaseModel):
    seat_count: int = Field(..., ge=1, le=500)


@router.get("")
def get_org_billing(current_user: UserInDB = Depends(get_current_user)):
    return billing.get_billing_summary(current_user.username)


@router.post("/checkout")
def org_checkout(body: OrgCheckoutBody, current_user: UserInDB = Depends(get_current_user)):
    m = service.require_membership(current_user.username, min_role="admin")
    if body.plan_id not in PLANS or body.plan_id == "free":
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    members = service.list_org_members(m["org_id"])
    if body.seat_count < len(members):
        raise HTTPException(
            status_code=400,
            detail=f"seat_count must be at least current member count ({len(members)})",
        )

    plan = PLANS[body.plan_id]
    amounts = calculate_order_amount(
        plan,
        billing_cycle=body.billing_cycle,
        seat_count=body.seat_count,
        cloud_costs_usd=body.cloud_costs_usd,
    )
    result = create_razorpay_order_record(
        order_type="org",
        payer_username=current_user.username,
        plan_id=body.plan_id,
        billing_cycle=body.billing_cycle,
        amounts=amounts,
        org_id=m["org_id"],
        seat_count=body.seat_count,
        cloud_costs_usd=body.cloud_costs_usd,
        receipt_prefix="org",
    )
    result["plan_name"] = plan.name
    return result


@router.post("/verify-payment")
def org_verify_payment(
    body: OrgVerifyPaymentBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    if not verify_razorpay_signature(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    completed = complete_paid_order(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        username=current_user.username,
    )
    order = completed["order"]
    if order.get("org_id") != m["org_id"]:
        raise HTTPException(status_code=403, detail="Order does not belong to your organization")

    activate_org_subscription(
        m["org_id"],
        plan_id=order["plan_id"],
        seat_count=int(order.get("seat_count") or 1),
        billing_cycle=order["billing_cycle"],
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        total_amount=float(order.get("total_amount") or 0),
        actor_username=current_user.username,
    )

    return {
        "success": True,
        "message": "Organization subscription activated",
        "plan_id": order["plan_id"],
        "seat_count": order.get("seat_count"),
        "valid_until": completed["current_period_end"],
    }


@router.patch("/seats")
def update_org_seats(body: OrgSeatsBody, current_user: UserInDB = Depends(get_current_user)):
    m = service.require_membership(current_user.username, min_role="admin")
    members = service.list_org_members(m["org_id"])
    if body.seat_count < len(members):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reduce below current member count ({len(members)})",
        )
    from app.database.mongo_client import get_database
    from bson import ObjectId

    get_database()["organizations"].update_one(
        {"_id": ObjectId(m["org_id"])},
        {"$set": {"seat_count": body.seat_count}},
    )
    service.invalidate_org_cache(m["org_id"])
    return billing.get_org_limits(m["org_id"])


@router.post("/cancel")
def cancel_billing(current_user: UserInDB = Depends(get_current_user)):
    return cancel_org_subscription(current_user.username)


@router.post("/migrate-personal")
def migrate_personal(current_user: UserInDB = Depends(get_current_user)):
    return billing.migrate_personal_subscription_to_org(current_user.username)
