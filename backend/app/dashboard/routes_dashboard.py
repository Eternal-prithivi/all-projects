from fastapi import APIRouter, Depends
from app.users.routes_users import get_current_user
from app.database.mongo_client import get_database
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# The prefix is now handled in main.py, so it's removed from here.
router = APIRouter(
    tags=["Dashboard"]
)

@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """
    Returns real statistics for the main dashboard overview.
    """
    DB = get_database()
    
    try:
        # Get real monthly costs from AWS
        from app.cost.manager import get_aws_cost_and_usage
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        monthly_costs = 0.0
        try:
            aws_data = get_aws_cost_and_usage(start_date, end_date, "DAILY")
            monthly_costs = sum(
                float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
                for item in aws_data.get("ResultsByTime", [])
            )
        except Exception as e:
            logger.warning(f"Could not fetch AWS costs: {e}")
            monthly_costs = 0.0
        
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
