"""
Consolidated Billing Routes - Simple Version
Manages invoices and billing without real payment integration
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..users.routes_users import get_current_user
from ..users.user_model import User
from ..database.mongo_client import get_database
import secrets

router = APIRouter(prefix="/billing", tags=["Billing"])
DB = get_database()


class CostBreakdown(BaseModel):
    aws: float = 0.0
    gcp: float = 0.0
    azure: float = 0.0
    platform_fee: float = 0.0


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
        
        # Calculate current month costs (mock data for now)
        current_month_costs = CostBreakdown(
            aws=125.50,
            gcp=89.30,
            azure=45.20,
            platform_fee=29.00
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
        
        # Mock costs (in production, these would come from actual cloud provider APIs)
        costs = CostBreakdown(
            aws=125.50,
            gcp=89.30,
            azure=45.20,
            platform_fee=29.00
        )
        
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
        # Mock current month costs
        # In production, this would aggregate costs from cost analysis data
        current_costs = CostBreakdown(
            aws=125.50,
            gcp=89.30,
            azure=45.20,
            platform_fee=29.00
        )
        
        total = current_costs.aws + current_costs.gcp + current_costs.azure + current_costs.platform_fee
        
        # Get days remaining in month
        now = datetime.utcnow()
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
