# backend/app/payments/routes_payments.py

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import stripe
from app.utils.config import settings
from app.database.mongo_client import get_database
from app.users.routes_users import get_current_user
from app.users.user_model import User

router = APIRouter()
DB = get_database()

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

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
    """Request to create checkout session"""
    plan_id: str = Field(..., description="Plan ID: 'free', 'basic', 'pro', 'enterprise'")
    billing_cycle: str = Field(..., description="'monthly' or 'yearly'")
    success_url: str = Field(default="https://rajverse.me/dashboard?payment=success")
    cancel_url: str = Field(default="https://rajverse.me/pricing?payment=cancelled")

class SubscriptionResponse(BaseModel):
    """Current subscription details"""
    subscription_id: Optional[str]
    plan_id: str
    plan_name: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    vm_limit: int
    storage_gb: int

# --- Pricing Plans ---

PLANS = {
    "free": PaymentPlan(
        plan_id="free",
        name="Free Tier",
        description="Perfect for testing and small projects",
        price_monthly=0,
        price_yearly=0,
        features=[
            "2 VMs (1 performance + 1 storage)",
            "10 GB storage per VM",
            "Basic monitoring",
            "Community support",
            "Demo mode (mock data)"
        ],
        vm_limit=2,
        storage_gb=10,
        priority_support=False
    ),
    "basic": PaymentPlan(
        plan_id="basic",
        name="Basic",
        description="Great for individuals and small teams",
        price_monthly=499,  # ₹499/month
        price_yearly=4990,  # ₹4,990/year (2 months free)
        features=[
            "5 VMs (3 performance + 2 storage)",
            "50 GB storage per VM",
            "Real-time monitoring",
            "Email support (24h response)",
            "Real cloud resources (AWS, GCP, Azure)"
        ],
        vm_limit=5,
        storage_gb=50,
        priority_support=False
    ),
    "pro": PaymentPlan(
        plan_id="pro",
        name="Professional",
        description="For growing businesses",
        price_monthly=1499,  # ₹1,499/month
        price_yearly=14990,  # ₹14,990/year (2 months free)
        features=[
            "15 VMs (10 performance + 5 storage)",
            "200 GB storage per VM",
            "Real-time monitoring + AI recommendations",
            "Priority email support (4h response)",
            "Multi-cloud optimization",
            "Cost analytics dashboard",
            "API access"
        ],
        vm_limit=15,
        storage_gb=200,
        priority_support=True
    ),
    "enterprise": PaymentPlan(
        plan_id="enterprise",
        name="Enterprise",
        description="Custom solutions for large organizations",
        price_monthly=4999,  # ₹4,999/month
        price_yearly=49990,  # ₹49,990/year (2 months free)
        features=[
            "Unlimited VMs",
            "1 TB storage per VM",
            "Real-time monitoring + AI + predictive analytics",
            "24/7 phone + email support (1h response)",
            "Dedicated account manager",
            "Custom integrations",
            "SLA guarantees",
            "White-label options"
        ],
        vm_limit=999,
        storage_gb=1000,
        priority_support=True
    )
}

# --- Helper Functions ---

def get_user_subscription(user_id: str) -> Dict[str, Any]:
    """Get user's current subscription from MongoDB"""
    subscription = DB["subscriptions"].find_one({"user_id": user_id})
    
    if not subscription:
        # Return free tier by default
        return {
            "user_id": user_id,
            "plan_id": "free",
            "status": "active",
            "subscription_id": None,
            "stripe_customer_id": None,
            "current_period_start": None,
            "current_period_end": None,
            "cancel_at_period_end": False
        }
    
    return subscription

def update_user_limits(user_id: str, plan_id: str):
    """Update user's VM and storage limits based on plan"""
    plan = PLANS[plan_id]
    
    DB["users"].update_one(
        {"username": user_id},
        {"$set": {
            "vm_limit": plan.vm_limit,
            "storage_limit_gb": plan.storage_gb,
            "plan_id": plan_id,
            "updated_at": datetime.utcnow()
        }}
    )

# --- API Endpoints ---

@router.get("/plans", response_model=List[PaymentPlan], summary="Get All Pricing Plans")
async def get_pricing_plans() -> List[PaymentPlan]:
    """
    Get all available subscription plans with pricing and features.
    """
    return list(PLANS.values())

@router.get("/my-subscription", response_model=SubscriptionResponse, summary="Get My Subscription")
async def get_my_subscription(
    current_user: User = Depends(get_current_user)
) -> SubscriptionResponse:
    """
    Get current user's subscription details.
    """
    subscription = get_user_subscription(current_user.username)
    plan = PLANS[subscription["plan_id"]]
    
    return SubscriptionResponse(
        subscription_id=subscription.get("subscription_id"),
        plan_id=subscription["plan_id"],
        plan_name=plan.name,
        status=subscription["status"],
        current_period_start=subscription.get("current_period_start"),
        current_period_end=subscription.get("current_period_end"),
        cancel_at_period_end=subscription.get("cancel_at_period_end", False),
        vm_limit=plan.vm_limit,
        storage_gb=plan.storage_gb
    )

@router.post("/create-checkout", summary="Create Stripe Checkout Session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Create a Stripe checkout session for upgrading subscription.
    Returns checkout URL to redirect user to Stripe payment page.
    """
    try:
        if request.plan_id not in PLANS or request.plan_id == "free":
            raise HTTPException(status_code=400, detail="Invalid plan ID")
        
        plan = PLANS[request.plan_id]
        
        # Calculate price based on billing cycle
        amount = plan.price_yearly if request.billing_cycle == "yearly" else plan.price_monthly
        
        # Get or create Stripe customer
        subscription_data = get_user_subscription(current_user.username)
        stripe_customer_id = subscription_data.get("stripe_customer_id")
        
        if not stripe_customer_id:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.username,
                metadata={
                    "user_id": current_user.username,
                    "plan_id": request.plan_id
                }
            )
            stripe_customer_id = customer.id
            
            # Save customer ID to MongoDB
            DB["subscriptions"].update_one(
                {"user_id": current_user.username},
                {"$set": {"stripe_customer_id": stripe_customer_id}},
                upsert=True
            )
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(amount * 100),  # Convert to paise
                    'product_data': {
                        'name': f"{plan.name} Plan - {request.billing_cycle.title()}",
                        'description': plan.description,
                    },
                    'recurring': {
                        'interval': 'year' if request.billing_cycle == 'yearly' else 'month',
                        'interval_count': 1,
                    }
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                'user_id': current_user.username,
                'plan_id': request.plan_id,
                'billing_cycle': request.billing_cycle
            }
        )
        
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")

@router.post("/webhook", summary="Stripe Webhook Handler")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks for subscription events.
    This endpoint is called by Stripe when subscription status changes.
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata']['user_id']
            plan_id = session['metadata']['plan_id']
            subscription_id = session.get('subscription')
            
            # Get subscription details from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Update subscription in MongoDB
            DB["subscriptions"].update_one(
                {"user_id": user_id},
                {"$set": {
                    "plan_id": plan_id,
                    "status": "active",
                    "subscription_id": subscription_id,
                    "stripe_customer_id": session['customer'],
                    "current_period_start": datetime.fromtimestamp(stripe_subscription.current_period_start),
                    "current_period_end": datetime.fromtimestamp(stripe_subscription.current_period_end),
                    "cancel_at_period_end": False,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
            
            # Update user limits
            update_user_limits(user_id, plan_id)
            
            print(f"✓ Subscription activated for user {user_id}: {plan_id}")
        
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            customer_id = subscription['customer']
            
            # Find user by customer ID
            sub_data = DB["subscriptions"].find_one({"stripe_customer_id": customer_id})
            if sub_data:
                DB["subscriptions"].update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {
                        "status": subscription['status'],
                        "current_period_start": datetime.fromtimestamp(subscription['current_period_start']),
                        "current_period_end": datetime.fromtimestamp(subscription['current_period_end']),
                        "cancel_at_period_end": subscription.get('cancel_at_period_end', False),
                        "updated_at": datetime.utcnow()
                    }}
                )
        
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription['customer']
            
            # Downgrade to free tier
            sub_data = DB["subscriptions"].find_one({"stripe_customer_id": customer_id})
            if sub_data:
                user_id = sub_data["user_id"]
                DB["subscriptions"].update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {
                        "plan_id": "free",
                        "status": "cancelled",
                        "subscription_id": None,
                        "updated_at": datetime.utcnow()
                    }}
                )
                update_user_limits(user_id, "free")
                print(f"✓ User {user_id} downgraded to free tier")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-subscription", summary="Cancel Subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel current subscription. Access continues until end of billing period.
    """
    try:
        subscription_data = get_user_subscription(current_user.username)
        
        if subscription_data["plan_id"] == "free":
            raise HTTPException(status_code=400, detail="You are on the free tier")
        
        subscription_id = subscription_data.get("subscription_id")
        if not subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Cancel at period end (don't immediately revoke access)
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        # Update MongoDB
        DB["subscriptions"].update_one(
            {"user_id": current_user.username},
            {"$set": {
                "cancel_at_period_end": True,
                "updated_at": datetime.utcnow()
            }}
        )
        
        period_end = subscription_data.get("current_period_end")
        
        return {
            "success": True,
            "message": "Subscription will be cancelled at the end of billing period",
            "access_until": period_end
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reactivate-subscription", summary="Reactivate Cancelled Subscription")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Reactivate a subscription that was cancelled but still within billing period.
    """
    try:
        subscription_data = get_user_subscription(current_user.username)
        subscription_id = subscription_data.get("subscription_id")
        
        if not subscription_id:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        if not subscription_data.get("cancel_at_period_end"):
            raise HTTPException(status_code=400, detail="Subscription is not cancelled")
        
        # Reactivate subscription
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )
        
        # Update MongoDB
        DB["subscriptions"].update_one(
            {"user_id": current_user.username},
            {"$set": {
                "cancel_at_period_end": False,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {
            "success": True,
            "message": "Subscription reactivated successfully"
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-history", summary="Get Payment History")
async def get_payment_history(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get payment history for the current user.
    """
    try:
        subscription_data = get_user_subscription(current_user.username)
        customer_id = subscription_data.get("stripe_customer_id")
        
        if not customer_id:
            return []
        
        # Retrieve payment intents from Stripe
        charges = stripe.Charge.list(customer=customer_id, limit=20)
        
        history = []
        for charge in charges.data:
            history.append({
                "id": charge.id,
                "amount": charge.amount / 100,  # Convert from paise to rupees
                "currency": charge.currency.upper(),
                "status": charge.status,
                "description": charge.description,
                "receipt_url": charge.receipt_url,
                "created": datetime.fromtimestamp(charge.created),
                "paid": charge.paid
            })
        
        return history
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
