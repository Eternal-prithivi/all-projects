# =============================================================================
# MODULE: routes_cost.py  (187 lines)
# PURPOSE: Cost analytics — historical cost data query, per-service breakdown,
#          CSV export, Z-score anomaly detection, decay-weighted linear regression forecast
# READS FROM:  cost_data collection
# DEPENDS ON:  forecasting.py (linear regression), tasks_anomaly.py (Celery Z-score alerts)
# MOUNTED AT:  /api/cost → cost-data, export/csv, anomalies, forecast
# DO NOT:
#   - Change the decay-weighted forecast formula — it's documented in the project report §5.3
#   - Remove the anomaly Z-score threshold without updating AI_RULES.md
# =============================================================================
# backend/app/cost/routes_cost.py

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import logging

from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
from app.config.demo_mode import is_demo_mode, MockDataGenerator, log_demo_mode_call
# from app.auth.jwthandler import get_current_user # Assuming you have JWT for auth
# from app.models.user import User # Assuming your User model is defined

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache for cost queries (1 hour TTL)
# Format: {"aws_2025-01-01_2025-01-31": (data, timestamp)}
cost_cache = {}
CACHE_TTL = 3600  # 1 hour in seconds
MAX_CACHE_ENTRIES = 50  # Prevent memory leak from unlimited cache growth

def add_to_cost_cache(cache_key: str, data: Any, timestamp: float):
    """Add entry to cache with size limit protection"""
    if len(cost_cache) >= MAX_CACHE_ENTRIES:
        # Remove oldest entry (smallest timestamp)
        oldest_key = min(cost_cache.keys(), key=lambda k: cost_cache[k][1])
        logger.info(f"Cache limit reached ({MAX_CACHE_ENTRIES}). Evicting oldest entry: {oldest_key}")
        del cost_cache[oldest_key]
    
    cost_cache[cache_key] = (data, timestamp)
    logger.debug(f"Cache entry added: {cache_key}. Total entries: {len(cost_cache)}")

# Placeholder for actual authentication if needed
# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     # Implement actual user validation here if required
#     return current_user

@router.get("/aws", summary="Get AWS Cost and Usage Data")
async def get_aws_costs(
    # current_user: User = Depends(get_current_active_user), # Uncomment when auth is ready
    start_date: str = Query(..., description="Start date for the report (YYYY-MM-DD). Max 13 months ago for DAILY."),
    end_date: str = Query(..., description="End date for the report (YYYY-MM-DD). Must be after start_date."),
    granularity: str = Query("DAILY", pattern="^(DAILY|MONTHLY)$", description="Granularity of the data (DAILY or MONTHLY)."),
    group_by_dimension: Optional[List[str]] = Query(None, description="Dimensions to group by (e.g., SERVICE, AZ, REGION)."),
    group_by_tag: Optional[List[str]] = Query(None, description="Tags to group by (e.g., CostCenter).")
) -> Dict[str, Any]:
    """
    Retrieves AWS Cost and Usage data from Cost Explorer (cached for 1 hour).
    """
    try:
        # Demo mode: Return mock data (zero API cost)
        if is_demo_mode():
            log_demo_mode_call("AWS Cost Explorer")
            mock_data = MockDataGenerator.mock_aws_cost_data(start_date, end_date, granularity)
            return {"provider": "aws", "data": mock_data, "cached": False, "demo_mode": True}
        
        # Create cache key from query parameters
        cache_key = f"aws_{start_date}_{end_date}_{granularity}"
        current_time = time.time()
        
        # Check cache first
        if cache_key in cost_cache:
            cached_data, cached_time = cost_cache[cache_key]
            if (current_time - cached_time) < CACHE_TTL:
                logger.info(f"Using cached AWS cost data for {cache_key}")
                return {"provider": "aws", "data": cached_data, "cached": True}
        
        # Cache miss or expired - fetch fresh data
        logger.info(f"Fetching fresh AWS cost data for {cache_key} (Cost Explorer API call)")
        
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
        
        # Update cache with size limit protection
        add_to_cost_cache(cache_key, cost_data, current_time)
        logger.info(f"AWS cost data cached for {cache_key}")
        
        return {"provider": "aws", "data": cost_data, "cached": False}
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

@router.get("/cache/stats", summary="Get Cache Statistics")
async def get_cache_stats():
    """
    Returns cache statistics for monitoring and debugging.
    Helps identify cache effectiveness and potential issues.
    """
    if not cost_cache:
        return {
            "total_entries": 0,
            "cache_empty": True,
            "message": "No cache entries yet"
        }
    
    current_time = time.time()
    active_entries = 0
    expired_entries = 0
    
    for cache_key, (data, timestamp) in cost_cache.items():
        if (current_time - timestamp) < CACHE_TTL:
            active_entries += 1
        else:
            expired_entries += 1
    
    # Find oldest and newest entries
    oldest_entry = min(cost_cache.items(), key=lambda x: x[1][1])
    newest_entry = max(cost_cache.items(), key=lambda x: x[1][1])
    
    oldest_age = int((current_time - oldest_entry[1][1]) / 60)  # minutes
    newest_age = int((current_time - newest_entry[1][1]) / 60)  # minutes
    
    return {
        "total_entries": len(cost_cache),
        "active_entries": active_entries,
        "expired_entries": expired_entries,
        "max_capacity": MAX_CACHE_ENTRIES,
        "utilization": f"{(len(cost_cache) / MAX_CACHE_ENTRIES * 100):.1f}%",
        "oldest_entry": {
            "key": oldest_entry[0],
            "age_minutes": oldest_age
        },
        "newest_entry": {
            "key": newest_entry[0],
            "age_minutes": newest_age
        },
        "cache_ttl_minutes": int(CACHE_TTL / 60)
    }

@router.delete("/cache/clear", summary="Clear Cost Cache")
async def clear_cost_cache():
    """
    Manually clear all cached cost data.
    Use this if you suspect stale or incorrect data in cache.
    Next request will fetch fresh data from AWS Cost Explorer ($0.01).
    """
    entries_cleared = len(cost_cache)
    cost_cache.clear()
    logger.info(f"Cost cache manually cleared. {entries_cleared} entries removed.")
    
    return {
        "success": True,
        "entries_cleared": entries_cleared,
        "message": "Cost cache cleared successfully. Next requests will fetch fresh data."
    }