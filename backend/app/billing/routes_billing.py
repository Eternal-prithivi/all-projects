"""
Consolidated Billing Routes - Simple Version
Manages invoices and billing without real payment integration
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..users.routes_users import get_current_user
from ..users.user_model import User
from ..database.mongo_client import get_database
from ..cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
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


# Cache for billing cost data (1 hour TTL)
billing_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 3600  # 1 hour
}


def fetch_real_cloud_costs(start_date: str, end_date: str, use_cache: bool = True) -> CostBreakdown:
    """
    Fetch real costs from cloud providers for the specified date range (cached for 1 hour)
    Returns CostBreakdown with actual costs or 0.0 if provider not configured
    """
    # Check cache first
    if use_cache:
        current_time = time.time()
        cache_key = f"{start_date}_{end_date}"
        if billing_cache["data"] is not None and (current_time - billing_cache["timestamp"]) < billing_cache["ttl"]:
            logger.info(f"Using cached billing cost data for {cache_key}")
            return billing_cache["data"]
    
    logger.info(f"Fetching fresh billing cost data for {start_date} to {end_date} (Cost Explorer API call)")
    costs = CostBreakdown()
    
    try:
        # Fetch AWS costs
        aws_data = get_aws_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity='MONTHLY',
            group_by=[]
        )
        if aws_data and 'ResultsByTime' in aws_data:
            aws_total = sum(
                float(period['Total']['UnblendedCost']['Amount']) 
                for period in aws_data['ResultsByTime']
            )
            costs.aws = round(aws_total, 2)
    except Exception as e:
        logger.error(f"AWS cost fetch failed: {e}")
        costs.aws = 0.0
    
    try:
        # Fetch GCP costs
        gcp_data = get_gcp_billing_data(start_date=start_date, end_date=end_date)
        if gcp_data and 'TotalCost' in gcp_data:
            costs.gcp = round(gcp_data['TotalCost'], 2)
        elif gcp_data and gcp_data.get('status') in ['missing_config', 'missing_dependency', 'error']:
            costs.gcp = 0.0
    except Exception as e:
        logger.error(f"GCP cost fetch failed: {e}")
        costs.gcp = 0.0
    
    try:
        # Fetch Azure costs
        azure_data = get_azure_billing_data(start_date=start_date, end_date=end_date)
        if azure_data and 'TotalCost' in azure_data:
            costs.azure = round(azure_data['TotalCost'], 2)
        elif azure_data and azure_data.get('status') in ['missing_config', 'missing_dependency', 'error']:
            costs.azure = 0.0
    except Exception as e:
        logger.error(f"Azure cost fetch failed: {e}")
        costs.azure = 0.0
    
    # Update cache
    if use_cache:
        billing_cache["data"] = costs
        billing_cache["timestamp"] = time.time()
        logger.info(f"Billing cost data cached")
    
    return costs


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
        
        current_month_costs = fetch_real_cloud_costs(start_of_month, end_date)
        
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
        
        costs = fetch_real_cloud_costs(start_of_month, end_date)
        
        total = costs.aws + costs.gcp + costs.azure + costs.platform_fee
        
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
        
        current_costs = fetch_real_cloud_costs(start_of_month, end_date)
        
        total = current_costs.aws + current_costs.gcp + current_costs.azure + current_costs.platform_fee
        
        # Get days remaining in month
        next_month = now.replace(day=1) + relativedelta(months=1)
        days_remaining = (next_month - now).days
        
        return {
            "success": True,
            "billing_period": now.strftime("%Y-%m"),
            "costs": current_costs.model_dump(),
            "total": round(total, 2),
            "days_remaining": days_remaining,
            "invoice_date": next_month.strftime("%Y-%m-%d")
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

