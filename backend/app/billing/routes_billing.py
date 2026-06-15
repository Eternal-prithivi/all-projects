# =============================================================================
# MODULE: billing/routes_billing.py  (386 lines)
# PURPOSE: Internal billing system — generate invoices from cost_data, list billing history,
#          download invoice PDF, mark invoices paid (mock — no real payment gateway here)
# NOTE: This is the internal billing layer. Stripe payments are in routes_payments.py
# READS FROM:  invoices, cost_data collections
# WRITES TO:   invoices collection
# MOUNTED AT:  /api/billing → invoices, generate, download/{id}, mark-paid
# DO NOT:
#   - Confuse this with routes_payments.py — billing is for invoices, payments is Stripe checkout
#   - Delete invoices — mark them void/paid instead to preserve audit trail
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..users.routes_users import get_current_user
from ..users.user_model import User
from ..database.mongo_client import get_database
from ..cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
from app.billing.storage_metering import (
    get_platform_storage_metering_summary,
    get_storage_metering_summary,
)
from app.payments.subscription_service import _owner_usernames
import secrets
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])
DB = get_database()


# Pydantic Models (must be defined before functions that use them)
class CostBreakdown(BaseModel):
    aws: float = 0.0
    gcp: float = 0.0
    azure: float = 0.0
    platform_fee: float = 29.00  # Fixed platform fee
    # Pass-through estimates for storage page list/sync/upload/download API calls
    storage_api_aws: float = 0.0
    storage_api_gcp: float = 0.0
    storage_api_azure: float = 0.0
    storage_api_total: float = 0.0

class BudgetSettings(BaseModel):
    monthly_budget: float = 0.0
    alert_threshold: float = 80.0  # Alert when spending reaches 80% of budget
    email_alerts: bool = True


class Invoice(BaseModel):
    invoice_id: str
    username: str
    billing_period: str  # Format: "2025-11"
    costs: CostBreakdown
    total: float
    status: str  # "paid", "pending", "overdue"
    due_date: datetime
    paid_date: Optional[datetime] = None
    created_at: datetime


class InvoiceResponse(BaseModel):
    success: bool
    invoice: Invoice


class InvoicesListResponse(BaseModel):
    success: bool
    invoices: List[Invoice]
    current_month_costs: CostBreakdown


# Cache for billing cost data (1 hour TTL) — keyed per user + date range to prevent
# cross-user data leakage when multiple users share the same process instance.
# Format: {cache_key: (CostBreakdown, timestamp)}
_billing_cache: Dict[str, Any] = {}
BILLING_CACHE_TTL = 3600  # 1 hour


def _billing_cache_key(username: str, start_date: str, end_date: str) -> str:
    return f"{username}:{start_date}:{end_date}"


def _billing_cache_get(key: str) -> Optional[Any]:
    entry = _billing_cache.get(key)
    if entry is None:
        return None
    data, ts = entry
    if (time.time() - ts) >= BILLING_CACHE_TTL:
        del _billing_cache[key]
        return None
    return data


def _billing_cache_set(key: str, data: Any) -> None:
    # Evict entries beyond 200 to avoid unbounded growth
    if len(_billing_cache) >= 200:
        oldest = min(_billing_cache, key=lambda k: _billing_cache[k][1])
        del _billing_cache[oldest]
    _billing_cache[key] = (data, time.time())


def fetch_real_cloud_costs(
    username: str, start_date: str, end_date: str, use_cache: bool = True
) -> CostBreakdown:
    """
    Fetch real costs from cloud providers for the specified date range (cached per user, 1 h TTL).
    Each (username, start_date, end_date) tuple gets its own cache slot so users can never
    see each other's cost data even within the same process.
    """
    cache_key = _billing_cache_key(username, start_date, end_date)

    if use_cache:
        cached = _billing_cache_get(cache_key)
        if cached is not None:
            logger.info(f"Using cached billing cost data for {cache_key}")
            return cached

    logger.info(f"Fetching fresh billing cost data for {username} {start_date}→{end_date}")
    costs = CostBreakdown()

    try:
        aws_data = get_aws_cost_and_usage(
            username,
            start_date=start_date,
            end_date=end_date,
            granularity='MONTHLY',
            group_by=[],
        )
        if aws_data and 'ResultsByTime' in aws_data:
            costs.aws = round(sum(
                float(p['Total']['UnblendedCost']['Amount'])
                for p in aws_data['ResultsByTime']
            ), 2)
    except Exception as e:
        logger.error(f"AWS cost fetch failed for {username}: {e}")

    try:
        gcp_data = get_gcp_billing_data(username, start_date=start_date, end_date=end_date)
        if gcp_data and 'TotalCost' in gcp_data:
            costs.gcp = round(gcp_data['TotalCost'], 2)
    except Exception as e:
        logger.error(f"GCP cost fetch failed for {username}: {e}")

    try:
        azure_data = get_azure_billing_data(username, start_date=start_date, end_date=end_date)
        if azure_data and 'TotalCost' in azure_data:
            costs.azure = round(azure_data['TotalCost'], 2)
    except Exception as e:
        logger.error(f"Azure cost fetch failed for {username}: {e}")

    if use_cache:
        _billing_cache_set(cache_key, costs)
        logger.info(f"Billing cost cached for {cache_key}")

    _apply_storage_api_metering(username, costs, start_date, end_date)
    return costs


def _apply_storage_api_metering(
    username: str, costs: CostBreakdown, start_date: str, end_date: str
) -> None:
    """Merge metered storage API estimates into CostBreakdown (current month periods)."""
    try:
        start_period = (start_date or "")[:7]
        end_period = (end_date or "")[:7]
        if not start_period or not end_period:
            return
        summary = get_storage_metering_summary(
            username, start_period=start_period, end_period=end_period
        )
        est = summary.get("estimated_usd") or {}
        costs.storage_api_aws = round(float(est.get("AWS", 0.0)), 6)
        costs.storage_api_gcp = round(float(est.get("GCP", 0.0)), 6)
        costs.storage_api_azure = round(float(est.get("Azure", 0.0)), 6)
        costs.storage_api_total = round(float(est.get("total", 0.0)), 6)
    except Exception as exc:
        logger.warning("storage_api_metering merge failed for %s: %s", username, exc)


@router.get("/storage-metering")
async def get_storage_metering(
    current_user: User = Depends(get_current_user),
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
):
    """Metered storage API usage (list buckets, sync, upload, download) for pass-through billing."""
    now = datetime.utcnow()
    period = start_period or now.strftime("%Y-%m")
    end = end_period or period
    summary = get_storage_metering_summary(
        current_user.username, start_period=period, end_period=end
    )
    return {"success": True, **summary}


@router.get("/storage-metering/platform")
async def get_platform_storage_metering(
    current_user: User = Depends(get_current_user),
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
):
    """Aggregate metered storage API usage across all users (platform operator only)."""
    if current_user.username not in _owner_usernames():
        raise HTTPException(status_code=403, detail="Platform operator access required.")
    now = datetime.utcnow()
    period = start_period or now.strftime("%Y-%m")
    end = end_period or period
    summary = get_platform_storage_metering_summary(
        start_period=period, end_period=end
    )
    return {"success": True, **summary}


@router.get("/invoices", response_model=InvoicesListResponse)
async def get_invoices(current_user: User = Depends(get_current_user)):
    """Get all invoices for the current user"""
    try:
        invoices_collection = DB["invoices"]
        
        # Get all invoices for user, sorted by billing period descending
        invoices = list(invoices_collection.find(
            {"username": current_user.username},
            {"_id": 0}
        ).sort("billing_period", -1))
        
        # Convert datetime strings back to datetime objects
        for invoice in invoices:
            invoice['created_at'] = datetime.fromisoformat(invoice['created_at'])
            invoice['due_date'] = datetime.fromisoformat(invoice['due_date'])
            if invoice.get('paid_date'):
                invoice['paid_date'] = datetime.fromisoformat(invoice['paid_date'])
        
        # Calculate current month costs using real data from cloud providers
        now = datetime.utcnow()
        start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        current_month_costs = fetch_real_cloud_costs(
            current_user.username, start_of_month, end_date
        )
        
        return InvoicesListResponse(
            success=True,
            invoices=[Invoice(**inv) for inv in invoices],
            current_month_costs=current_month_costs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoices: {str(e)}")


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific invoice by ID"""
    try:
        invoices_collection = DB["invoices"]
        
        invoice = invoices_collection.find_one(
            {"invoice_id": invoice_id, "username": current_user.username},
            {"_id": 0}
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Convert datetime strings back to datetime objects
        invoice['created_at'] = datetime.fromisoformat(invoice['created_at'])
        invoice['due_date'] = datetime.fromisoformat(invoice['due_date'])
        if invoice.get('paid_date'):
            invoice['paid_date'] = datetime.fromisoformat(invoice['paid_date'])
        
        return InvoiceResponse(
            success=True,
            invoice=Invoice(**invoice)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoice: {str(e)}")


@router.post("/invoices/generate", response_model=InvoiceResponse)
async def generate_invoice(current_user: User = Depends(get_current_user)):
    """
    Generate a new invoice for the current user
    In production, this would be a cron job that runs monthly
    """
    try:
        invoices_collection = DB["invoices"]
        
        # Get current month and year
        now = datetime.utcnow()
        billing_period = now.strftime("%Y-%m")
        
        # Check if invoice already exists for this period
        existing = invoices_collection.find_one({
            "username": current_user.username,
            "billing_period": billing_period
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Invoice already exists for this period")
        
        # Generate invoice ID
        invoice_id = f"INV-{now.strftime('%Y%m')}-{secrets.token_hex(3).upper()}"
        
        # Fetch real costs from cloud providers for the current month
        start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        costs = fetch_real_cloud_costs(current_user.username, start_of_month, end_date)
        
        total = (
            costs.aws
            + costs.gcp
            + costs.azure
            + costs.storage_api_total
            + costs.platform_fee
        )
        
        # Due date is 7 days from creation
        due_date = now + timedelta(days=7)
        
        invoice_data = {
            "invoice_id": invoice_id,
            "username": current_user.username,
            "billing_period": billing_period,
            "costs": costs.model_dump(),
            "total": round(total, 2),
            "status": "pending",
            "due_date": due_date.isoformat(),
            "paid_date": None,
            "created_at": now.isoformat()
        }
        
        invoices_collection.insert_one(invoice_data)
        
        # Convert back to datetime for response
        invoice_data['created_at'] = now
        invoice_data['due_date'] = due_date
        
        return InvoiceResponse(
            success=True,
            invoice=Invoice(**invoice_data)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate invoice: {str(e)}")


@router.put("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(invoice_id: str, current_user: User = Depends(get_current_user)):
    """
    Mark an invoice as paid (manual payment simulation)
    In production with real payments, this would be triggered by webhook
    """
    try:
        invoices_collection = DB["invoices"]
        
        # Find the invoice
        invoice = invoices_collection.find_one({
            "invoice_id": invoice_id,
            "username": current_user.username
        })
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice['status'] == 'paid':
            raise HTTPException(status_code=400, detail="Invoice is already paid")
        
        # Mark as paid
        paid_date = datetime.utcnow()
        result = invoices_collection.update_one(
            {"invoice_id": invoice_id},
            {
                "$set": {
                    "status": "paid",
                    "paid_date": paid_date.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update invoice")
        
        return {
            "success": True,
            "message": "Invoice marked as paid",
            "invoice_id": invoice_id,
            "paid_date": paid_date
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark invoice as paid: {str(e)}")


@router.get("/current-month-summary")
async def get_current_month_summary(current_user: User = Depends(get_current_user)):
    """Get current month's running costs (not yet invoiced)"""
    try:
        # Fetch real costs from cloud providers for the current month
        now = datetime.utcnow()
        start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        current_costs = fetch_real_cloud_costs(current_user.username, start_of_month, end_date)
        
        total = (
            current_costs.aws
            + current_costs.gcp
            + current_costs.azure
            + current_costs.storage_api_total
            + current_costs.platform_fee
        )
        
        # Get days remaining in month
        next_month = now.replace(day=1) + relativedelta(months=1)
        days_remaining = (next_month - now).days
        
        period = now.strftime("%Y-%m")
        storage_detail = get_storage_metering_summary(
            current_user.username, start_period=period, end_period=period
        )
        return {
            "success": True,
            "billing_period": period,
            "costs": current_costs.model_dump(),
            "storage_metering": storage_detail,
            "total": round(total, 6),
            "days_remaining": days_remaining,
            "invoice_date": next_month.strftime("%Y-%m-%d"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch current month summary: {str(e)}")


@router.get("/budget")
async def get_budget(current_user: User = Depends(get_current_user)):
    """Get user's budget settings"""
    try:
        users_collection = DB["users"]
        user = users_collection.find_one({"username": current_user.username})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        budget_settings = user.get("budget_settings", {
            "monthly_budget": 0.0,
            "alert_threshold": 80.0,
            "email_alerts": True
        })
        
        return {
            "success": True,
            "budget": budget_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch budget: {str(e)}")


@router.put("/budget")
async def update_budget(
    budget: BudgetSettings, 
    current_user: User = Depends(get_current_user)
):
    """Update user's budget settings"""
    try:
        users_collection = DB["users"]
        
        result = users_collection.update_one(
            {"username": current_user.username},
            {"$set": {"budget_settings": budget.model_dump()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "message": "Budget settings updated successfully",
            "budget": budget.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")

