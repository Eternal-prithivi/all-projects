# =============================================================================
# MODULE: routes_payments.py  (579 lines)
# PURPOSE: Stripe payment integration — subscription plans, checkout session creation,
#          webhook event handling, subscription status checks
# READS FROM:  users collection (subscription_tier field)
# WRITES TO:   users collection (subscription_tier, stripe_customer_id)
# DEPENDS ON:  Stripe SDK, settings.STRIPE_SECRET_KEY, settings.STRIPE_WEBHOOK_SECRET
# MOUNTED AT:  /api/payments → create-checkout, webhook, status, cancel
# DO NOT:
#   - Log or store raw Stripe webhook payloads — they contain sensitive card data
#   - Change plan IDs without updating the Stripe dashboard price IDs too
#   - Skip webhook signature verification — it prevents replay attacks
# =============================================================================
# backend/app/payments/routes_payments.py

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import razorpay
import hmac
import hashlib
from app.utils.config import settings
from app.database.mongo_client import get_database
from app.users.routes_users import get_current_user
from app.users.user_model import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()
DB = get_database()

# Initialize Razorpay
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# --- Pydantic Models ---

class PaymentPlan(BaseModel):
    """Available subscription plans"""
    plan_id: str
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    features: List[str]
    vm_limit: int
    storage_gb: int
    priority_support: bool

class CheckoutRequest(BaseModel):
    """Request to create checkout/payment"""
    plan_id: str = Field(..., description="Plan ID: 'free', 'basic', 'pro', 'enterprise'")
    billing_cycle: str = Field(..., description="'monthly' or 'yearly'")
    cloud_costs_usd: float = Field(0.0, description="Cloud usage costs in USD to be added to subscription")

class SubscriptionResponse(BaseModel):
    """Current subscription details"""
    subscription_id: Optional[str]
    plan_id: str
    plan_name: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    auto_renew: bool
    vm_limit: int
    storage_gb: int
    managed_by_org: bool = False
    org_id: Optional[str] = None
    org_name: Optional[str] = None
    seat_count: Optional[int] = None
    seats_used: Optional[int] = None
    can_manage_billing: Optional[bool] = None


class NavEntitlementItem(BaseModel):
    id: str
    locked: bool
    min_plan: Optional[str] = None


class PlanEntitlementsResponse(BaseModel):
    plan_id: str
    plan_name: str
    limits: Dict[str, Any]
    features: Dict[str, bool]
    nav: List[NavEntitlementItem]

# --- Pricing Plans ---

PLANS = {
    "free": PaymentPlan(
        plan_id="free",
        name="Free",
        description="Explore Zenith with demo dashboards and platform cloud",
        price_monthly=0,
        price_yearly=0,
        features=[
            "1 micro VM (CSP free-tier class)",
            "5 GB storage (CSP free-tier aligned)",
            "Demo cost dashboard & cached VM metrics",
            "Storage uploads via platform cloud (when configured)",
            "Static-site provision templates on platform keys",
            "Community support (Help Center)",
        ],
        vm_limit=1,
        storage_gb=5,
        priority_support=False,
    ),
    "basic": PaymentPlan(
        plan_id="basic",
        name="Basic",
        description="Real multi-cloud ops for solo builders",
        price_monthly=499,  # ₹499/month
        price_yearly=4990,  # ₹4,990/year (2 months free)
        features=[
            "5 VMs + active provisioned stacks (shared quota)",
            "50 GB org storage",
            "Live AWS · GCP · Azure via platform keys",
            "Intelligent storage tiering recommendations",
            "Infrastructure Build wizard (Terraform + SDK)",
            "Cost & usage dashboard with live billing data",
            "Email support (24h response)",
        ],
        vm_limit=5,
        storage_gb=50,
        priority_support=False,
    ),
    "pro": PaymentPlan(
        plan_id="pro",
        name="Pro",
        description="Teams with BYOC, governance, and AI insights",
        price_monthly=1499,  # ₹1,499/month
        price_yearly=14990,  # ₹14,990/year (2 months free)
        features=[
            "15 VMs + active provisioned stacks",
            "200 GB org storage",
            "BYOC — connect your AWS · GCP · Azure accounts",
            "Org billing with seat-based subscriptions",
            "Provision policies, audit log & approval guardrails",
            "AI storage & cost recommendations",
            "Priority email support (4h response)",
            "REST API access",
        ],
        vm_limit=15,
        storage_gb=200,
        priority_support=True,
    ),
    "enterprise": PaymentPlan(
        plan_id="enterprise",
        name="Enterprise",
        description="Org-wide governance, unlimited scale, dedicated onboarding",
        price_monthly=4999,  # ₹4,999/month
        price_yearly=49990,  # ₹49,990/year (2 months free)
        features=[
            "Unlimited VMs & provisioned stacks",
            "1 TB org storage quota",
            "Everything in Pro + hybrid BYOC & platform routing",
            "Org resource ACL, reassign & budget approvals",
            "Custom provision policies & exportable audit log",
            "Team spend rollups & optimization recommendations",
            "Dedicated onboarding — contact sales for custom SLA",
        ],
        vm_limit=999,
        storage_gb=1000,
        priority_support=True,
    ),
}

# --- Helper Functions ---

def get_user_subscription(user_id: str) -> Dict[str, Any]:
    """Get user's current subscription (MongoDB + owner env + legacy users.plan_id)."""
    from app.payments.subscription_service import get_user_subscription as _resolve

    return _resolve(user_id)


def update_user_limits(user_id: str, plan_id: str):
    """Update user's VM and storage limits based on plan"""
    from app.payments.subscription_service import apply_user_plan_limits

    apply_user_plan_limits(user_id, plan_id)

# --- API Endpoints ---

@router.get("/plans", response_model=List[PaymentPlan], summary="Get All Pricing Plans")
async def get_pricing_plans() -> List[PaymentPlan]:
    """
    Get all available subscription plans with pricing and features.
    """
    return list(PLANS.values())


@router.get(
    "/entitlements",
    response_model=PlanEntitlementsResponse,
    summary="Get plan entitlements for current user",
)
async def get_plan_entitlements(
    current_user: User = Depends(get_current_user),
) -> PlanEntitlementsResponse:
    """Feature flags, quotas, and nav lock metadata for dashboard gating."""
    from app.payments.plan_entitlements import get_entitlements

    payload = get_entitlements(current_user.username)
    return PlanEntitlementsResponse(**payload)


@router.get("/my-subscription", response_model=SubscriptionResponse, summary="Get My Subscription")
async def get_my_subscription(
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """
    Get current user's subscription details.
    """
    from app.payments.subscription_service import get_effective_subscription

    subscription = get_effective_subscription(current_user.username)
    plan = PLANS[subscription["plan_id"]]

    return SubscriptionResponse(
        subscription_id=subscription.get("subscription_id"),
        plan_id=subscription["plan_id"],
        plan_name=subscription.get("plan_name") or plan.name,
        status=subscription["status"],
        current_period_start=subscription.get("current_period_start"),
        current_period_end=subscription.get("current_period_end"),
        auto_renew=subscription.get("auto_renew", True),
        vm_limit=subscription.get("vm_limit") or plan.vm_limit,
        storage_gb=subscription.get("storage_gb") or plan.storage_gb,
        managed_by_org=bool(subscription.get("managed_by_org")),
        org_id=subscription.get("org_id"),
        org_name=subscription.get("org_name"),
        seat_count=subscription.get("seat_count"),
        seats_used=subscription.get("seats_used"),
        can_manage_billing=subscription.get("can_manage_billing"),
    )

@router.post("/create-order", summary="Create Razorpay Order")
async def create_razorpay_order(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a Razorpay order for subscription payment.
    Returns order details to initiate payment on frontend.
    """
    from app.payments.subscription_service import user_in_org_with_billing

    if user_in_org_with_billing(current_user.username):
        raise HTTPException(
            status_code=400,
            detail="Your plan is managed by your organization. Ask an admin to upgrade on Team or Billing.",
        )

    try:
        if request.plan_id not in PLANS or request.plan_id == "free":
            raise HTTPException(status_code=400, detail="Invalid plan ID")

        plan = PLANS[request.plan_id]
        
        # Calculate price based on billing cycle
        subscription_amount = plan.price_yearly if request.billing_cycle == "yearly" else plan.price_monthly
        
        from app.config.billing_constants import FX_USD_TO_INR

        cloud_costs_inr = request.cloud_costs_usd * FX_USD_TO_INR
        
        # Total amount = subscription + cloud costs
        total_amount = subscription_amount + cloud_costs_inr
        amount_paise = int(total_amount * 100)  # Convert to paise
        
        # Create Razorpay order
        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"order_{current_user.username}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "notes": {
                "user_id": current_user.username,
                "plan_id": request.plan_id,
                "billing_cycle": request.billing_cycle,
                "plan_name": plan.name
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        # Save pending order to MongoDB
        DB["payment_orders"].insert_one({
            "order_id": order["id"],
            "user_id": current_user.username,
            "plan_id": request.plan_id,
            "billing_cycle": request.billing_cycle,
            "subscription_amount": subscription_amount,
            "cloud_costs_usd": request.cloud_costs_usd,
            "cloud_costs_inr": cloud_costs_inr,
            "total_amount": total_amount,
            "status": "created",
            "created_at": datetime.utcnow()
        })
        
        return {
            "order_id": order["id"],
            "amount": total_amount,
            "subscription_amount": subscription_amount,
            "cloud_costs_inr": cloud_costs_inr,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,  # Frontend needs this
            "plan_name": plan.name,
            "billing_cycle": request.billing_cycle
        }
        
    except HTTPException:
        raise
    except razorpay.errors.BadRequestError as e:
        raise HTTPException(status_code=400, detail=f"Razorpay error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")


def activate_subscription_from_payment_order(
    order: dict,
    *,
    username: str,
    razorpay_payment_id: str,
    razorpay_order_id: str,
) -> datetime:
    """Activate subscription from a paid Razorpay order (verify-payment or webhook)."""
    from app.payments.subscription_service import set_user_subscription

    billing_cycle = order["billing_cycle"]
    current_period_start = datetime.utcnow()
    current_period_end = (
        current_period_start + timedelta(days=365)
        if billing_cycle == "yearly"
        else current_period_start + timedelta(days=30)
    )
    set_user_subscription(
        username,
        order["plan_id"],
        status="active",
        razorpay_payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id,
        billing_cycle=billing_cycle,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        auto_renew=True,
    )
    DB["payment_orders"].update_one(
        {"order_id": razorpay_order_id},
        {
            "$set": {
                "status": "paid",
                "payment_id": razorpay_payment_id,
                "paid_at": datetime.utcnow(),
            }
        },
    )
    DB["payments"].insert_one(
        {
            "username": username,
            "plan_id": order["plan_id"],
            "amount": order["total_amount"],
            "currency": "INR",
            "status": "success",
            "payment_method": "razorpay",
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "billing_cycle": billing_cycle,
            "created_at": datetime.utcnow(),
        }
    )
    return current_period_end


@router.post("/verify-payment", summary="Verify Razorpay Payment")
async def verify_payment(
    payment_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """
    Verify payment signature and activate subscription.
    Called from frontend after successful payment.
    """
    try:
        # Extract payment details
        razorpay_order_id = payment_data.get("razorpay_order_id")
        razorpay_payment_id = payment_data.get("razorpay_payment_id")
        razorpay_signature = payment_data.get("razorpay_signature")
        
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            raise HTTPException(status_code=400, detail="Missing payment details")
        
        # Verify signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != razorpay_signature:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # Get order details from MongoDB
        order = DB["payment_orders"].find_one({"order_id": razorpay_order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        current_period_end = activate_subscription_from_payment_order(
            order,
            username=current_user.username,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
        )

        logger.info(f"Subscription activated for user {current_user.username}: {order['plan_id']}")

        return {
            "success": True,
            "message": "Payment verified and subscription activated",
            "plan_id": order["plan_id"],
            "valid_until": current_period_end,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@router.post("/webhook", summary="Razorpay Webhook Handler")
async def razorpay_webhook(request: Request):
    """
    Handle Razorpay webhooks for payment events.
    This endpoint is called by Razorpay when payment status changes.
    """
    try:
        payload = await request.body()
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        # Verify webhook signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                payload.decode(),
                webhook_signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
        except razorpay.errors.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse webhook event
        import json
        event = json.loads(payload)
        event_type = event.get("event")
        
        # Handle payment.captured event
        if event_type == "payment.captured":
            payment = event["payload"]["payment"]["entity"]
            order_id = payment.get("order_id")
            
            if order_id:
                # Find order in MongoDB
                order = DB["payment_orders"].find_one({"order_id": order_id})
                if order and order.get("status") != "paid":
                    username = order.get("user_id") or order.get("username")
                    if username:
                        activate_subscription_from_payment_order(
                            order,
                            username=username,
                            razorpay_payment_id=payment["id"],
                            razorpay_order_id=order_id,
                        )
                    else:
                        DB["payment_orders"].update_one(
                            {"order_id": order_id},
                            {
                                "$set": {
                                    "status": "paid",
                                    "payment_id": payment["id"],
                                    "paid_at": datetime.utcnow(),
                                }
                            },
                        )
                        DB["payments"].insert_one(
                            {
                                "username": order.get("user_id"),
                                "plan_id": order["plan_id"],
                                "amount": order["total_amount"],
                                "currency": "INR",
                                "status": "success",
                                "payment_method": "razorpay",
                                "razorpay_order_id": order_id,
                                "razorpay_payment_id": payment["id"],
                                "billing_cycle": order["billing_cycle"],
                                "created_at": datetime.utcnow(),
                            }
                        )

                    logger.info(f"Payment captured for order {order_id}")
        
        # Handle payment.failed event
        elif event_type == "payment.failed":
            payment = event["payload"]["payment"]["entity"]
            order_id = payment.get("order_id")
            
            if order_id:
                order = DB["payment_orders"].find_one({"order_id": order_id})
                if order:
                    DB["payment_orders"].update_one(
                        {"order_id": order_id},
                        {"$set": {
                            "status": "failed",
                            "failed_at": datetime.utcnow(),
                            "error_description": payment.get("error_description")
                        }}
                    )
                    
                    # Create failed payment record
                    DB["payments"].insert_one({
                        "username": order["user_id"],
                        "plan_id": order["plan_id"],
                        "amount": order["total_amount"],
                        "currency": "INR",
                        "status": "failed",
                        "payment_method": "razorpay",
                        "razorpay_order_id": order_id,
                        "billing_cycle": order["billing_cycle"],
                        "error_description": payment.get("error_description"),
                        "created_at": datetime.utcnow()
                    })
                    username = order.get("user_id") or order.get("username")
                    if username:
                        DB["subscriptions"].update_one(
                            {"$or": [{"user_id": username}, {"username": username}]},
                            {"$set": {"status": "past_due", "updated_at": datetime.utcnow()}},
                        )

                    logger.warning(f"Payment failed for order {order_id}")

        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-subscription", summary="Cancel Subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel current subscription. For Razorpay, we disable auto-renewal.
    Access continues until end of billing period.
    """
    try:
        subscription_data = get_user_subscription(current_user.username)
        
        if subscription_data["plan_id"] == "free":
            raise HTTPException(status_code=400, detail="You are on the free tier")
        
        # Update MongoDB to disable auto-renewal
        DB["subscriptions"].update_one(
            {"user_id": current_user.username},
            {"$set": {
                "auto_renew": False,
                "updated_at": datetime.utcnow()
            }}
        )
        
        period_end = subscription_data.get("current_period_end")
        
        return {
            "success": True,
            "message": "Subscription will not auto-renew. Access continues until end of billing period.",
            "access_until": period_end
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reactivate-subscription", summary="Reactivate Subscription")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reactivate auto-renewal for subscription that was cancelled.
    """
    try:
        subscription_data = get_user_subscription(current_user.username)
        
        if subscription_data["plan_id"] == "free":
            raise HTTPException(status_code=404, detail="No subscription found")
        
        if subscription_data.get("auto_renew"):
            raise HTTPException(status_code=400, detail="Subscription is already active")
        
        # Check if subscription is still valid
        current_period_end = subscription_data.get("current_period_end")
        if current_period_end and datetime.utcnow() > current_period_end:
            raise HTTPException(status_code=400, detail="Subscription has expired. Please purchase a new plan.")
        
        # Enable auto-renewal
        DB["subscriptions"].update_one(
            {"user_id": current_user.username},
            {"$set": {
                "auto_renew": True,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {
            "success": True,
            "message": "Auto-renewal reactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-history", summary="Get Payment History")
async def get_payment_history(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get payment history for the current user from MongoDB.
    """
    try:
        # Get all paid orders for this user
        orders = DB["payment_orders"].find({
            "user_id": current_user.username,
            "status": "paid"
        }).sort("paid_at", -1).limit(20)
        
        history = []
        for order in orders:
            history.append({
                "id": order["order_id"],
                "amount": order["amount"],
                "currency": "INR",
                "status": order["status"],
                "plan_id": order.get("plan_id"),
                "billing_cycle": order.get("billing_cycle"),
                "payment_id": order.get("payment_id"),
                "created": order.get("created_at"),
                "paid_at": order.get("paid_at")
            })
        
        return history
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payment history: {str(e)}")
