# =============================================================================
# MODULE: dashboard/routes_dashboard.py
# PURPOSE: Mission Control data — aggregate stats for the main dashboard bento-grid
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException
from app.users.routes_users import get_current_user
from app.database.mongo_client import get_database
from app.dashboard.cost_aggregation import get_cached_user_costs, refresh_user_costs
from app.dashboard.cost_snapshots import get_cost_trend
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """
    Returns real statistics for the main dashboard overview.
    Monthly cost = sum of all available providers (BYOC + platform hybrid).
    Does not call cloud billing APIs — use POST /refresh-costs for a live refresh.
    """
    DB = get_database()

    try:
        cost_snapshot = get_cached_user_costs(user.username)
        monthly_costs = cost_snapshot.get("monthly_costs", 0.0) or 0.0

        vm_assignments = DB["vm_assignments"]
        active_vms = vm_assignments.count_documents(
            {"user_id": user.username, "status": "assigned"}
        )

        files_collection = DB["files"]
        user_files_filter = {"owner_username": user.username}
        total_files = files_collection.count_documents(user_files_filter)

        storage_agg = list(
            files_collection.aggregate(
                [
                    {"$match": user_files_filter},
                    {
                        "$group": {
                            "_id": None,
                            "bytes": {
                                "$sum": {"$ifNull": ["$size_bytes", {"$ifNull": ["$size", 0]}]}
                            },
                        }
                    },
                ]
            )
        )
        total_size_bytes = storage_agg[0]["bytes"] if storage_agg else 0
        storage_used_tb = round(total_size_bytes / (1024 ** 4), 2)

        secure_files = DB["secure_files"]
        security_alerts = secure_files.count_documents(
            {
                "owner_username": user.username,
                "is_sensitive": True,
                "is_encrypted": False,
            }
        )

        vm_metrics = DB["vm_metrics"]
        vm_health = {"healthy": 0, "warning": 0, "critical": 0}
        metrics_cutoff = datetime.utcnow() - timedelta(hours=24)

        pipeline = [
            {"$match": {"timestamp": {"$gte": metrics_cutoff}}},
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
    from app.payments.plan_entitlements import require_feature

    require_feature(user.username, "live_billing")
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
