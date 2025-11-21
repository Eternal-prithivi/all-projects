from fastapi import APIRouter, Depends, HTTPException
from app.users.routes_users import get_current_user
from app.database.mongo_client import get_database
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)

# Cache for AWS cost data (1 hour TTL)
aws_cost_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 3600  # 1 hour in seconds
}

# The prefix is now handled in main.py, so it's removed from here.
router = APIRouter(
    tags=["Dashboard"]
)

@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """
    Returns real statistics for the main dashboard overview.
    Uses cached AWS cost data (1 hour TTL).
    """
    DB = get_database()
    
    try:
        # Get cached monthly costs from AWS (no API call)
        monthly_costs = aws_cost_cache.get("data", 0.0) or 0.0
        
        # Get real VM count
        vm_assignments = DB["vm_assignments"]
        active_vms = vm_assignments.count_documents({"status": "assigned"})
        
        # Get real storage usage
        files_collection = DB["files"]
        total_files = files_collection.count_documents({})
        
        # Calculate total storage in TB (assuming average file size)
        total_size_bytes = 0
        for file_doc in files_collection.find({}, {"size": 1}):
            total_size_bytes += file_doc.get("size", 0)
        storage_used_tb = round(total_size_bytes / (1024 ** 4), 2)  # Convert bytes to TB
        
        # Get security alerts (from secure_files collection)
        secure_files = DB["secure_files"]
        security_alerts = secure_files.count_documents({"has_sensitive_data": True, "is_encrypted": False})
        
        # Get VM health status from latest metrics
        vm_metrics = DB["vm_metrics"]
        vm_health = {"healthy": 0, "warning": 0, "critical": 0}
        
        # Get latest metrics for each VM
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$vm_name",
                "latest_cpu": {"$first": "$cpu_utilization"},
                "latest_memory": {"$first": "$memory_utilization"}
            }}
        ]
        
        for vm_metric in vm_metrics.aggregate(pipeline):
            cpu = vm_metric.get("latest_cpu", 0)
            memory = vm_metric.get("latest_memory", 0)
            
            # Classify health based on CPU and memory
            if cpu > 90 or memory > 90:
                vm_health["critical"] += 1
            elif cpu > 70 or memory > 70:
                vm_health["warning"] += 1
            else:
                vm_health["healthy"] += 1
        
        return {
            "monthly_costs": round(monthly_costs, 2),
            "active_vms": active_vms,
            "storage_used_tb": storage_used_tb if storage_used_tb > 0 else 0.1,  # Show 0.1 if no storage
            "security_alerts": security_alerts,
            "total_files": total_files,
            "vm_health": vm_health
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        # Return safe defaults on error
        return {
            "monthly_costs": 0.0,
            "active_vms": 0,
            "storage_used_tb": 0.0,
            "security_alerts": 0,
            "total_files": 0,
            "vm_health": {"healthy": 0, "warning": 0, "critical": 0}
        }

@router.post("/refresh-costs")
async def refresh_aws_costs(user: dict = Depends(get_current_user)):
    """
    Manually refresh AWS cost data (triggers Cost Explorer API call).
    Use this sparingly to avoid API charges ($0.01 per call).
    """
    from app.cost.manager import get_aws_cost_and_usage
    
    try:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        logger.info("Manual refresh: Fetching AWS cost data")
        aws_data = get_aws_cost_and_usage(start_date, end_date, "DAILY")
        monthly_costs = sum(
            float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
            for item in aws_data.get("ResultsByTime", [])
        )
        
        # Update cache
        aws_cost_cache["data"] = monthly_costs
        aws_cost_cache["timestamp"] = time.time()
        
        logger.info(f"AWS costs refreshed: ${monthly_costs:.2f}")
        
        return {
            "success": True,
            "monthly_costs": round(monthly_costs, 2),
            "cached_at": datetime.utcnow().isoformat(),
            "message": "Cost data refreshed successfully (Cost Explorer API call made)"
        }
    except Exception as e:
        logger.error(f"Error refreshing AWS costs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh costs: {str(e)}")
