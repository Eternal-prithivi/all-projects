"""Billing connectivity routes."""

from fastapi import APIRouter, Depends

from app.cost.billing_status import get_user_billing_status
from app.users.routes_users import get_current_user
from app.users.user_model import User

router = APIRouter(tags=["Cost Connectivity"])


@router.get("/billing-status", summary="Per-user billing connectivity for AWS/GCP/Azure")
async def billing_status(user: User = Depends(get_current_user)):
    """
    Probe whether live billing data is available per provider for the current user.
    Does not return dollar amounts — only connectivity and setup hints.
    """
    return get_user_billing_status(user.username)
