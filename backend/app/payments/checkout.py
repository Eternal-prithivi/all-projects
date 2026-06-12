"""Shared Razorpay checkout helpers for user and org billing."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import razorpay
from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.utils.config import settings

DB = get_database()
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def verify_razorpay_signature(
    order_id: str, payment_id: str, signature: str
) -> bool:
    generated = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return generated == signature


def calculate_order_amount(
    plan,
    *,
    billing_cycle: str,
    seat_count: int = 1,
    cloud_costs_usd: float = 0.0,
) -> Dict[str, float]:
    from app.config.billing_constants import FX_USD_TO_INR

    unit = plan.price_yearly if billing_cycle == "yearly" else plan.price_monthly
    subscription_amount = float(unit) * max(1, seat_count)
    cloud_costs_inr = cloud_costs_usd * FX_USD_TO_INR
    total_amount = subscription_amount + cloud_costs_inr
    return {
        "subscription_amount": subscription_amount,
        "cloud_costs_inr": cloud_costs_inr,
        "total_amount": total_amount,
        "amount_paise": int(total_amount * 100),
    }


def create_razorpay_order_record(
    *,
    order_type: str,
    payer_username: str,
    plan_id: str,
    billing_cycle: str,
    amounts: Dict[str, float],
    org_id: Optional[str] = None,
    seat_count: int = 1,
    cloud_costs_usd: float = 0.0,
    receipt_prefix: str = "order",
) -> Dict[str, Any]:
    receipt = f"{receipt_prefix}_{payer_username}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    order_data = {
        "amount": amounts["amount_paise"],
        "currency": "INR",
        "receipt": receipt,
        "notes": {
            "user_id": payer_username,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle,
            "order_type": order_type,
            "seat_count": str(seat_count),
        },
    }
    if org_id:
        order_data["notes"]["org_id"] = org_id

    order = razorpay_client.order.create(data=order_data)

    DB["payment_orders"].insert_one(
        {
            "order_id": order["id"],
            "order_type": order_type,
            "user_id": payer_username,
            "org_id": org_id,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle,
            "seat_count": seat_count,
            "subscription_amount": amounts["subscription_amount"],
            "cloud_costs_usd": cloud_costs_usd,
            "cloud_costs_inr": amounts["cloud_costs_inr"],
            "total_amount": amounts["total_amount"],
            "status": "created",
            "created_at": datetime.utcnow(),
        }
    )

    return {
        "order_id": order["id"],
        "amount": amounts["total_amount"],
        "subscription_amount": amounts["subscription_amount"],
        "cloud_costs_inr": amounts["cloud_costs_inr"],
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "billing_cycle": billing_cycle,
        "seat_count": seat_count,
    }


def complete_paid_order(
    order_id: str,
    payment_id: str,
    *,
    username: str,
) -> Dict[str, Any]:
    order = DB["payment_orders"].find_one({"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    billing_cycle = order["billing_cycle"]
    current_period_start = datetime.utcnow()
    current_period_end = (
        current_period_start + timedelta(days=365)
        if billing_cycle == "yearly"
        else current_period_start + timedelta(days=30)
    )

    DB["payment_orders"].update_one(
        {"order_id": order_id},
        {
            "$set": {
                "status": "paid",
                "payment_id": payment_id,
                "paid_at": datetime.utcnow(),
            }
        },
    )

    DB["payments"].insert_one(
        {
            "username": username,
            "org_id": order.get("org_id"),
            "plan_id": order["plan_id"],
            "amount": order["total_amount"],
            "currency": "INR",
            "status": "success",
            "payment_method": "razorpay",
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "billing_cycle": billing_cycle,
            "seat_count": order.get("seat_count", 1),
            "order_type": order.get("order_type", "user"),
            "created_at": datetime.utcnow(),
        }
    )

    return {
        "order": order,
        "current_period_start": current_period_start,
        "current_period_end": current_period_end,
    }
