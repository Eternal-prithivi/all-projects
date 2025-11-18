from fastapi import APIRouter, Depends
from app.users.routes_users import get_current_user

# The prefix is now handled in main.py, so it's removed from here.
router = APIRouter(
    tags=["Dashboard"]
)

@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """
    Returns simulated statistics for the main dashboard overview.
    """
    return {
        "monthly_costs": 2345.67,
        "active_vms": 18,
        "storage_used_tb": 8.2,
        "security_alerts": 5
    }
