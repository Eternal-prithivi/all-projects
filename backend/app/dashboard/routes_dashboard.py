# =============================================================================
# MODULE: dashboard/routes_dashboard.py
# PURPOSE: Mission Control data — aggregate stats for the main dashboard bento-grid
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException
from app.users.routes_users import get_current_user
from app.database.mongo_client import get_database
from app.dashboard.cost_aggregation import get_cached_user_costs, refresh_user_costs
from app.dashboard.cost_snapshots import get_cost_trend
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """
    Returns real statistics for the main dashboard overview.
    Monthly cost = sum of all available providers (BYOC + platform hybrid).
    """
    DB = get_database()

    try:
        cost_snapshot = get_cached_user_costs(user.username)
        if not cost_snapshot.get("providers_included"):
            try:
                cost_snapshot = refresh_user_costs(user.username)
            except Exception as refresh_err:
                logger.warning("Initial dashboard cost refresh skipped: %s", refresh_err)
        monthly_costs = cost_snapshot.get("monthly_costs", 0.0) or 0.0

        vm_assignments = DB["vm_assignments"]
        active_vms = vm_assignments.count_documents({"status": "assigned"})

        files_collection = DB["files"]
        total_files = files_collection.count_documents({})

        total_size_bytes = 0
        for file_doc in files_collection.find({}, {"size": 1, "size_bytes": 1}):
            total_size_bytes += file_doc.get("size_bytes") or file_doc.get("size", 0)
        storage_used_tb = round(total_size_bytes / (1024 ** 4), 2)

        secure_files = DB["secure_files"]
        security_alerts = secure_files.count_documents(
            {"is_sensitive": True, "is_encrypted": False}
        )

        vm_metrics = DB["vm_metrics"]
        vm_health = {"healthy": 0, "warning": 0, "critical": 0}

        pipeline = [
            {"$sort": {"timestamp": -1}},
            {
                "$group": {
                    "_id": "$vm_name",
                    "latest_cpu": {"$first": "$cpu_utilization"},
                    "latest_memory": {"$first": "$memory_utilization"},
                }
            },
        ]

        for vm_metric in vm_metrics.aggregate(pipeline):
            cpu = vm_metric.get("latest_cpu", 0)
            memory = vm_metric.get("latest_memory", 0)

            if cpu > 90 or memory > 90:
                vm_health["critical"] += 1
            elif cpu > 70 or memory > 70:
                vm_health["warning"] += 1
            else:
                vm_health["healthy"] += 1

        return {
            "monthly_costs": round(monthly_costs, 2),
            "cost_by_provider": cost_snapshot.get("cost_by_provider", {}),
            "cost_providers_included": cost_snapshot.get("providers_included", []),
            "active_vms": active_vms,
            "storage_used_tb": storage_used_tb if storage_used_tb > 0 else 0.1,
            "security_alerts": security_alerts,
            "total_files": total_files,
            "vm_health": vm_health,
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        return {
            "monthly_costs": 0.0,
            "cost_by_provider": {},
            "cost_providers_included": [],
            "active_vms": 0,
            "storage_used_tb": 0.0,
            "security_alerts": 0,
            "total_files": 0,
            "vm_health": {"healthy": 0, "warning": 0, "critical": 0},
        }


@router.get("/recent-activity")
async def get_recent_activity(limit: int = 4, user: dict = Depends(get_current_user)):
    """Returns recent activity across VM assignments, file uploads, and security events."""
    DB = get_database()
    activities = []

    try:
        for doc in DB["vm_assignments"].find(
            {"user_id": user.username},
            {"vm_name": 1, "assigned_at": 1, "status": 1, "cluster_type": 1},
        ).sort("assigned_at", -1).limit(limit):
            ts = doc.get("assigned_at")
            activities.append(
                {
                    "id": str(doc["_id"]),
                    "type": "vm",
                    "action": f"VM assigned: {doc.get('vm_name', 'N/A')}",
                    "resource": f"{doc.get('cluster_type', '')} Cluster",
                    "status": "success" if doc.get("status") == "assigned" else "info",
                    "timestamp": ts.isoformat() if ts else "",
                    "time": _relative_time(ts),
                }
            )

        for doc in DB["files"].find(
            {"owner_username": user.username},
            {"filename": 1, "upload_date": 1, "csp": 1, "size_bytes": 1},
        ).sort("upload_date", -1).limit(limit):
            ts = doc.get("upload_date")
            activities.append(
                {
                    "id": str(doc["_id"]),
                    "type": "upload",
                    "action": f"Uploaded: {doc.get('filename', 'N/A')}",
                    "resource": doc.get("csp", "Storage"),
                    "status": "success",
                    "timestamp": ts.isoformat() if ts else "",
                    "time": _relative_time(ts),
                }
            )

        for doc in DB["secure_files"].find(
            {"owner_username": user.username},
            {"filename": 1, "upload_date": 1, "is_encrypted": 1},
        ).sort("upload_date", -1).limit(limit):
            ts = doc.get("upload_date")
            enc = "Encrypted" if doc.get("is_encrypted") else "Scanned"
            activities.append(
                {
                    "id": str(doc["_id"]),
                    "type": "security",
                    "action": f"Secure upload: {doc.get('filename', 'N/A')}",
                    "resource": enc,
                    "status": "success",
                    "timestamp": ts.isoformat() if ts else "",
                    "time": _relative_time(ts),
                }
            )

        activities.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
        return activities[:limit]

    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        return []


def _relative_time(dt):
    if not dt:
        return ""
    now = datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%b %d")


@router.get("/cost-trend")
async def dashboard_cost_trend(days: int = 7, user: dict = Depends(get_current_user)):
    """Last N days of stored cost snapshots — Mongo only, no cloud API calls."""
    return get_cost_trend(user.username, days=days)


@router.post("/refresh-costs")
async def refresh_dashboard_costs(user: dict = Depends(get_current_user)):
    """
    Refresh monthly spend for every cost provider available to this user (hybrid).
    Total = sum of AWS + GCP + Azure where each is available (BYOC and/or platform).
    """
    try:
        payload = refresh_user_costs(user.username, force=True)
        from app.config.demo_mode import is_demo_mode

        msg = (
            "Cost data refreshed (demo mock — no billing API call)"
            if is_demo_mode()
            else (
                f"Cost data refreshed for: {', '.join(p.upper() for p in payload.get('providers_included', []))}"
                or "No billing providers returned data"
            )
        )
        return {
            "success": True,
            "monthly_costs": payload["monthly_costs"],
            "cost_by_provider": payload.get("cost_by_provider", {}),
            "providers_included": payload.get("providers_included", []),
            "providers_skipped": payload.get("providers_skipped", {}),
            "cached_at": payload.get("cached_at"),
            "demo_mode": payload.get("demo_mode", False),
            "message": msg,
        }
    except Exception as e:
        logger.error(f"Error refreshing dashboard costs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh costs: {str(e)}")
