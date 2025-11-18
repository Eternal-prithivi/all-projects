# backend/app/cost/routes_cost.py

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

print("DEBUG in routes_cost.py: routes_cost.py is about to import from app.cost.manager.") # Diagnostic line
from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
# from app.auth.jwthandler import get_current_user # Assuming you have JWT for auth
# from app.models.user import User # Assuming your User model is defined

router = APIRouter()

# Placeholder for actual authentication if needed
# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     # Implement actual user validation here if required
#     return current_user

@router.get("/aws", summary="Get AWS Cost and Usage Data")
async def get_aws_costs(
    # current_user: User = Depends(get_current_active_user), # Uncomment when auth is ready
    start_date: str = Query(..., description="Start date for the report (YYYY-MM-DD). Max 13 months ago for DAILY."),
    end_date: str = Query(..., description="End date for the report (YYYY-MM-DD). Must be after start_date."),
    granularity: str = Query("DAILY", regex="^(DAILY|MONTHLY)$", description="Granularity of the data (DAILY or MONTHLY)."),
    group_by_dimension: Optional[List[str]] = Query(None, description="Dimensions to group by (e.g., SERVICE, AZ, REGION)."),
    group_by_tag: Optional[List[str]] = Query(None, description="Tags to group by (e.g., CostCenter).")
) -> Dict[str, Any]:
    """
    Retrieves AWS Cost and Usage data from Cost Explorer.
    """
    try:
        # Build group_by parameter for AWS Cost Explorer
        group_by_params = []
        if group_by_dimension:
            for dim in group_by_dimension:
                group_by_params.append({'Type': 'DIMENSION', 'Key': dim.upper()})
        if group_by_tag:
            for tag in group_by_tag:
                group_by_params.append({'Type': 'TAG', 'Key': tag})

        cost_data = get_aws_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            group_by=group_by_params
        )
        return {"provider": "aws", "data": cost_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch AWS costs: {e}")

@router.get("/gcp", summary="Get GCP Billing Data")
async def get_gcp_costs(
    # current_user: User = Depends(get_current_active_user), # Uncomment when auth is ready
    start_date: str = Query(..., description="Start date for the report (YYYY-MM-DD)."),
    end_date: str = Query(..., description="End date for the report (YYYY-MM-DD). Must be after start_date.")
) -> Dict[str, Any]:
    """
    Retrieves GCP Billing data.
    """
    try:
        cost_data = get_gcp_billing_data(start_date=start_date, end_date=end_date)
        return {"provider": "gcp", "data": cost_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch GCP costs: {e}")

@router.get("/azure", summary="Get Azure Cost Data")
async def get_azure_costs(
    # current_user: User = Depends(get_current_active_user), # Uncomment when auth is ready
    start_date: str = Query(..., description="Start date for the report (YYYY-MM-DD)."),
    end_date: str = Query(..., description="End date for the report (YYYY-MM-DD). Must be after start_date.")
) -> Dict[str, Any]:
    """
    Retrieves Azure Cost data.
    """
    try:
        cost_data = get_azure_billing_data(start_date=start_date, end_date=end_date)
        return {"provider": "azure", "data": cost_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Azure costs: {e}")