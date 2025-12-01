# backend/app/vm/tasks.py
"""
Celery background tasks for VM management.
- Periodic metrics collection from GCP Monitoring API
- Auto-release inactive VMs to save costs
- Scheduled health checks and alerts
"""

from app.celery_worker import celery_app
from app.vm.metrics_collector import VMMetricsCollector
from app.vm.manager import release_vm_assignment, get_cluster_health
from app.database.mongo_client import get_database
from app.utils.config import settings
from app.utils.logger import setup_logger
from datetime import datetime, timedelta
import asyncio
from typing import List

logger = setup_logger(__name__)
DB = get_database()
vm_assignments_collection = DB["vm_assignments"]
vm_metrics_collection = DB["vm_metrics"]


@celery_app.task(name="collect_vm_metrics")
def collect_vm_metrics_task():
    """
    Collect real-time metrics for all running VMs.
    Runs every 5 minutes via Celery Beat.
    """
    logger.info(f"Starting VM metrics collection")
    
    collector = VMMetricsCollector(
        project_id=settings.GCP_PROJECT_ID,
        zone=settings.GCP_ZONE
    )
    
    # List of all VMs to monitor
    all_vms = [
        "general-vm-1", "general-vm-2",
        "storage-vm-1", "storage-vm-2"
    ]
    
    collected_count = 0
    failed_count = 0
    
    for vm_name in all_vms:
        try:
            # Collect metrics asynchronously
            metrics = asyncio.run(collector.collect_all_metrics(vm_name))
            
            # Store in MongoDB
            metrics_doc = {
                "vm_name": metrics.vm_name,
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "disk_io_mb": metrics.disk_io_mb,
                "network_io_mb": metrics.network_io_mb,
                "active_users": metrics.active_users,
                "uptime_hours": metrics.uptime_hours,
                "estimated_cost_usd": metrics.estimated_cost_usd,
                "status": metrics.status.value,
                "collected_at": datetime.utcnow()
            }
            
            vm_metrics_collection.insert_one(metrics_doc)
            collected_count += 1
            logger.info(f"Collected metrics for {vm_name}: CPU={metrics.cpu_usage}%, MEM={metrics.memory_usage}%")
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to collect metrics for {vm_name}: {e}")
    
    logger.info(f"Metrics collection complete: {collected_count} succeeded, {failed_count} failed")
    
    return {
        "success": True,
        "collected": collected_count,
        "failed": failed_count,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(name="auto_release_inactive_vms")
def auto_release_inactive_vms_task():
    """
    Auto-release VMs that have been inactive for > 30 minutes.
    Stops VMs with zero users to save costs.
    Runs every 10 minutes via Celery Beat.
    """
    logger.info(f"Checking for inactive VM assignments")
    
    inactivity_threshold = datetime.utcnow() - timedelta(minutes=30)
    
    # Find active assignments with no recent activity
    inactive_assignments = vm_assignments_collection.find({
        "status": "ACTIVE",
        "last_active": {"$lt": inactivity_threshold}
    })
    
    released_count = 0
    stopped_vms = []
    
    for assignment in inactive_assignments:
        user_id = assignment["user_id"]
        vm_name = assignment["vm_name"]
        
        try:
            # Release assignment
            result = asyncio.run(release_vm_assignment(user_id))
            
            if result["success"]:
                released_count += 1
                
                if result["vm_stopped"]:
                    stopped_vms.append(vm_name)
                    logger.info(f"Released {user_id} from {vm_name} (VM stopped - no remaining users)")
                else:
                    logger.info(f"Released {user_id} from {vm_name} (VM still running - {result['remaining_users']} users remain)")
            
        except Exception as e:
            logger.error(f"Failed to release {user_id} from {vm_name}: {e}")
    
    logger.info(f"Auto-release complete: {released_count} assignments released, {len(stopped_vms)} VMs stopped")
    
    return {
        "success": True,
        "released_assignments": released_count,
        "stopped_vms": stopped_vms,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(name="cluster_health_check")
def cluster_health_check_task():
    """
    Periodic health check for all clusters.
    Sends alerts if CPU > 80% or user count exceeds safe limits.
    Runs every 15 minutes via Celery Beat.
    """
    logger.info(f"Running cluster health checks")
    
    from app.vm.models import ClusterType
    
    alerts = []
    
    for cluster_type in [ClusterType.GENERAL, ClusterType.STORAGE]:
        try:
            health = asyncio.run(get_cluster_health(cluster_type))
            
            # Alert conditions
            if health["average_cpu_usage"] > 80:
                alerts.append({
                    "severity": "HIGH",
                    "cluster": cluster_type.value,
                    "message": f"CPU overload: {health['average_cpu_usage']:.1f}% average",
                    "recommendation": "Consider starting additional VM or load balancing"
                })
            
            if health["total_active_users"] > health["total_vms"] * 4:  # More than 4 users per VM
                alerts.append({
                    "severity": "MEDIUM",
                    "cluster": cluster_type.value,
                    "message": f"High user density: {health['total_active_users']} users on {health['running_vms']} VMs",
                    "recommendation": "Start additional VM to distribute load"
                })
            
            if health["running_vms"] == 0 and health["total_active_users"] > 0:
                alerts.append({
                    "severity": "CRITICAL",
                    "cluster": cluster_type.value,
                    "message": "No running VMs but users are assigned!",
                    "recommendation": "Start VM immediately"
                })
            
            logger.info(f"{cluster_type.value} cluster: {health['running_vms']}/{health['total_vms']} VMs running, "
                  f"{health['total_active_users']} users, {health['average_cpu_usage']:.1f}% avg CPU")
            
        except Exception as e:
            logger.error(f"Failed health check for {cluster_type.value}: {e}")
    
    if alerts:
        logger.warning(f"{len(alerts)} alerts generated")
        for alert in alerts:
            logger.warning(f"[{alert['severity']}] {alert['cluster']}: {alert['message']}")
            # TODO: Send alerts via email/Slack/SNS
    else:
        logger.info("All clusters healthy")
    
    return {
        "success": True,
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(name="cleanup_old_metrics")
def cleanup_old_metrics_task():
    """
    Delete metrics older than 7 days to save MongoDB storage.
    Runs daily at midnight via Celery Beat.
    """
    logger.info(f"Cleaning up old metrics")
    
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    
    result = vm_metrics_collection.delete_many({
        "collected_at": {"$lt": cutoff_date}
    })
    
    deleted_count = result.deleted_count
    logger.info(f"Deleted {deleted_count} old metric records")
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }


# --- Celery Beat Schedule Configuration ---
# Add this to backend/app/celery_worker.py:
"""
celery_app.conf.beat_schedule = {
    'collect-vm-metrics-every-5-minutes': {
        'task': 'collect_vm_metrics',
        'schedule': 300.0,  # 5 minutes
    },
    'auto-release-inactive-vms-every-10-minutes': {
        'task': 'auto_release_inactive_vms',
        'schedule': 600.0,  # 10 minutes
    },
    'cluster-health-check-every-15-minutes': {
        'task': 'cluster_health_check',
        'schedule': 900.0,  # 15 minutes
    },
    'cleanup-old-metrics-daily': {
        'task': 'cleanup_old_metrics',
        'schedule': crontab(hour=0, minute=0),  # Midnight
    },
}
"""
