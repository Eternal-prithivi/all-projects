# =============================================================================
# MODULE: routes_admin.py  (989 lines)
# PURPOSE: Admin-only user management — list/create/delete users, change roles,
#          ban/unban, bulk operations, audit log query + CSV export
# READS FROM:  users, admin_actions collections
# WRITES TO:   users, admin_actions collections
# DEPENDS ON:  auth_utils.get_current_user(), require_admin() role guard
# MOUNTED AT:  (no prefix) → /admin/dashboard, /admin/users/*, /audit-logs
# DO NOT:
#   - Remove self-protection guards — admin cannot delete/ban/demote themselves
#   - Change admin_actions log schema — audit log query/export depends on it
#   - Add any endpoint without the require_admin() dependency
# =============================================================================


from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from ..database.mongo_client import get_database
from ..auth.auth_utils import get_current_user
from app.utils.logger import setup_logger
from app.auth.auth_utils import get_password_hash
from app.utils.audit_log import categorize_audit_action, dedupe_audit_entries
from fastapi.responses import Response
import io, csv

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])
DB = get_database()


# Pydantic Models
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_vms: int
    total_storage_gb: float
    total_revenue: float
    monthly_revenue: float
    subscription_breakdown: dict
    growth_rate: float


class UserOverview(BaseModel):
    username: str
    email: str
    role: str
    created_at: datetime
    last_login: Optional[datetime]
    subscription_plan: str
    active_vms: int
    storage_used_gb: float
    total_spent: float
    status: str


# Helper function to verify admin
async def verify_admin(current_user = Depends(get_current_user)):
    """Verify that the current user has admin role"""
    logger.debug(f"Admin auth check for user: {current_user}")
    logger.debug(f"User type: {type(current_user)}")
    logger.debug(f"User role: {getattr(current_user, 'role', 'NO ROLE ATTR')}")
    
    # Handle both dict and UserInDB object
    user_role = getattr(current_user, 'role', None) or (current_user.get('role') if isinstance(current_user, dict) else None)
    
    if user_role != "admin":
        logger.warning(f"Admin access denied - role is '{user_role}', not 'admin'")
        raise HTTPException(
            status_code=403,
            detail="Access denied. Admin privileges required."
        )
    
    logger.debug(f"Admin access granted")
    return current_user


def _get_admin_username(admin_user) -> str:
    """Extract the admin's username from either a dict or UserInDB object."""
    return getattr(admin_user, 'username', None) or (
        admin_user.get('username') if isinstance(admin_user, dict) else None
    )


@router.get("/dashboard", response_model=AdminStats)
async def get_admin_dashboard(admin_user: dict = Depends(verify_admin)):
    """
    Get admin dashboard statistics.
    Requires admin role.
    """
    try:
        # Total users
        total_users = DB["users"].count_documents({})
        
        # Active users (logged in last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users = DB["users"].count_documents({
            "last_login": {"$gte": thirty_days_ago}
        })
        
        # Total VMs
        total_vms = DB["vm_assignments"].count_documents({})
        
        # Total storage (sum of all file sizes)
        storage_pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$size_kb"}}}
        ]
        storage_result = list(DB["files"].aggregate(storage_pipeline))
        total_storage_gb = (storage_result[0]["total"] / 1024 / 1024) if storage_result and len(storage_result) > 0 else 0
        
        # Total revenue (sum of all successful payments)
        revenue_pipeline = [
            {"$match": {"status": "success"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        revenue_result = list(DB["payments"].aggregate(revenue_pipeline))
        total_revenue = revenue_result[0]["total"] if revenue_result and len(revenue_result) > 0 else 0
        
        # Monthly revenue (last 30 days)
        monthly_pipeline = [
            {"$match": {
                "status": "success",
                "created_at": {"$gte": thirty_days_ago}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        monthly_result = list(DB["payments"].aggregate(monthly_pipeline))
        monthly_revenue = monthly_result[0]["total"] if monthly_result and len(monthly_result) > 0 else 0
        
        # Subscription breakdown
        subscription_pipeline = [
            {"$group": {"_id": "$plan_id", "count": {"$sum": 1}}}
        ]
        sub_results = list(DB["users"].aggregate(subscription_pipeline))
        subscription_breakdown = {
            item["_id"] or "free": item["count"] for item in sub_results
        }
        
        # Ensure at least free tier exists
        if not subscription_breakdown:
            subscription_breakdown = {"free": total_users}
        
        # Growth rate (user growth last 30 days vs previous 30 days)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        new_users_last_month = DB["users"].count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
        new_users_prev_month = DB["users"].count_documents({
            "created_at": {"$gte": sixty_days_ago, "$lt": thirty_days_ago}
        })
        growth_rate = 0
        if new_users_prev_month > 0:
            growth_rate = ((new_users_last_month - new_users_prev_month) / new_users_prev_month) * 100
        
        logger.info(f"Admin dashboard stats calculated: users={total_users}, vms={total_vms}, revenue={total_revenue}")
        
        return AdminStats(
            total_users=total_users,
            active_users=active_users,
            total_vms=total_vms,
            total_storage_gb=round(total_storage_gb, 2),
            total_revenue=total_revenue,
            monthly_revenue=monthly_revenue,
            subscription_breakdown=subscription_breakdown,
            growth_rate=round(growth_rate, 2)
        )
    
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch admin stats: {str(e)}")


@router.get("/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    admin_user: dict = Depends(verify_admin)
):
    """
    Get all users with pagination and search.
    Requires admin role.
    """
    try:
        # Build query
        query = {}
        if search:
            query = {
                "$or": [
                    {"username": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}}
                ]
            }
        
        # Get users
        users_cursor = DB["users"].find(query).skip(skip).limit(limit)
        users = []
        
        for user in users_cursor:
            # Get user's VM count
            vm_count = DB["vm_assignments"].count_documents({"username": user["username"]})
            
            # Get user's storage usage
            storage_pipeline = [
                {"$match": {"username": user["username"]}},
                {"$group": {"_id": None, "total": {"$sum": "$size_kb"}}}
            ]
            storage_result = list(DB["files"].aggregate(storage_pipeline))
            storage_gb = (storage_result[0]["total"] / 1024 / 1024) if storage_result and len(storage_result) > 0 else 0
            
            # Get user's total spending
            spending_pipeline = [
                {"$match": {"username": user["username"], "status": "success"}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            spending_result = list(DB["payments"].aggregate(spending_pipeline))
            total_spent = spending_result[0]["total"] if spending_result and len(spending_result) > 0 else 0
            
            # Get last login from sessions
            last_session = DB["sessions"].find_one(
                {"username": user["username"]},
                sort=[("last_active", -1)]
            )
            last_login = last_session["last_active"] if last_session else None
            
            users.append({
                "username": user["username"],
                "email": user["email"],
                "role": user.get("role", "user"),
                "created_at": user.get("created_at"),
                "last_login": last_login,
                "subscription_plan": user.get("plan_id", "free"),
                "active_vms": vm_count,
                "storage_used_gb": round(storage_gb, 2),
                "total_spent": total_spent,
                "status": user.get("status", "active")
            })
        
        # Get total count for pagination
        total_count = DB["users"].count_documents(query)
        
        logger.info(f"Admin users: Returning {len(users)} users (total: {total_count})")
        
        return {
            "users": users,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"Admin users error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.put("/users/{username}/status")
async def update_user_status(
    username: str,
    status: str,
    admin_user: dict = Depends(verify_admin)
):
    """
    Update user status (active, suspended, banned).
    Requires admin role.
    """
    if status not in ["active", "suspended", "banned"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be: active, suspended, or banned")

    acting_admin = _get_admin_username(admin_user)
    if username == acting_admin:
        raise HTTPException(status_code=400, detail="Cannot change your own status through admin endpoints")
    
    try:
        result = DB["users"].update_one(
            {"username": username},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log the action
        DB["admin_actions"].insert_one({
            "admin_username": acting_admin,
            "action": "update_user_status",
            "target_user": username,
            "new_status": status,
            "timestamp": datetime.utcnow()
        })
        
        logger.info(f"Admin action: {acting_admin} updated {username} status to {status}")
        
        return {"success": True, "message": f"User {username} status updated to {status}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin action error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update user status: {str(e)}")


# --- New admin user management endpoints (create / delete / role / bulk) ---


class CreateUserPayload(BaseModel):
    username: str
    email: str
    password: Optional[str] = None
    role: Optional[str] = "user"
    plan_id: Optional[str] = "free"


@router.post("/users")
async def create_user(
    payload: CreateUserPayload,
    admin_user = Depends(verify_admin)
):
    """Create a new user (admin only). Password will be hashed if provided."""
    try:
        # Check uniqueness
        if DB["users"].find_one({"username": payload.username}):
            raise HTTPException(status_code=400, detail="Username already exists")

        if DB["users"].find_one({"email": payload.email}):
            raise HTTPException(status_code=400, detail="Email already exists")

        user_doc = {
            "username": payload.username,
            "email": payload.email,
            "role": payload.role or "user",
            "plan_id": payload.plan_id or "free",
            "created_at": datetime.utcnow(),
            "status": "active"
        }

        if payload.password:
            user_doc["hashed_password"] = get_password_hash(payload.password)

        DB["users"].insert_one(user_doc)

        plan_id = payload.plan_id or "free"
        if plan_id != "free":
            from app.payments.subscription_service import set_user_subscription

            set_user_subscription(payload.username, plan_id)

        # Log admin action
        DB["admin_actions"].insert_one({
            "admin_username": getattr(admin_user, 'username', admin_user.get('username') if isinstance(admin_user, dict) else None),
            "action": "create_user",
            "target_user": payload.username,
            "timestamp": datetime.utcnow()
        })

        return {"success": True, "message": f"User {payload.username} created"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    admin_user = Depends(verify_admin),
    soft: bool = True
):
    """Delete (soft) a user. Soft delete sets status=deleted; hard delete removes document if soft=False."""
    acting_admin = _get_admin_username(admin_user)
    if username == acting_admin:
        raise HTTPException(status_code=400, detail="Cannot delete your own account through admin endpoints")

    try:
        if soft:
            result = DB["users"].update_one({"username": username}, {"$set": {"status": "deleted", "deleted_at": datetime.utcnow()}})
        else:
            result = DB["users"].delete_one({"username": username})

        # UpdateResult has matched_count; DeleteResult has deleted_count — use getattr for both
        matched = getattr(result, 'matched_count', 0)
        deleted = getattr(result, 'deleted_count', 0)
        if matched == 0 and deleted == 0:
            raise HTTPException(status_code=404, detail="User not found")

        DB["admin_actions"].insert_one({
            "admin_username": acting_admin,
            "action": "delete_user",
            "target_user": username,
            "soft": soft,
            "timestamp": datetime.utcnow()
        })

        return {"success": True, "message": f"User {username} {'soft-deleted' if soft else 'deleted'}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RoleUpdatePayload(BaseModel):
    role: str


@router.put("/users/{username}/role")
async def update_user_role(
    username: str,
    payload: RoleUpdatePayload,
    admin_user = Depends(verify_admin)
):
    """Change a user's role."""
    acting_admin = _get_admin_username(admin_user)
    if username == acting_admin:
        raise HTTPException(status_code=400, detail="Cannot change your own role through admin endpoints")

    try:
        if payload.role not in ["user", "admin", "moderator"]:
            raise HTTPException(status_code=400, detail="Invalid role")

        result = DB["users"].update_one({"username": username}, {"$set": {"role": payload.role, "updated_at": datetime.utcnow()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        DB["admin_actions"].insert_one({
            "admin_username": acting_admin,
            "action": "change_role",
            "target_user": username,
            "new_role": payload.role,
            "timestamp": datetime.utcnow()
        })

        return {"success": True, "message": f"Role for {username} updated to {payload.role}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update role failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BulkUserActionItem(BaseModel):
    username: str
    action: str
    value: Optional[str] = None


class BulkUserActionRequest(BaseModel):
    items: List[BulkUserActionItem]


@router.post("/users/bulk")
async def bulk_user_actions(
    request: BulkUserActionRequest,
    admin_user = Depends(verify_admin)
):
    """Perform bulk user actions: activate/suspend/ban/delete/set_role."""
    acting_admin = _get_admin_username(admin_user)
    results = []
    try:
        for item in request.items:
            try:
                # Prevent admin from modifying themselves in bulk operations
                if item.username == acting_admin:
                    results.append({"username": item.username, "action": item.action, "ok": False, "error": "Cannot modify your own account"})
                    continue

                if item.action in ["activate", "suspend", "ban"]:
                    status = "active" if item.action == "activate" else ("suspended" if item.action == "suspend" else "banned")
                    DB["users"].update_one({"username": item.username}, {"$set": {"status": status, "updated_at": datetime.utcnow()}})
                    results.append({"username": item.username, "action": item.action, "ok": True})
                elif item.action == "delete":
                    DB["users"].update_one({"username": item.username}, {"$set": {"status": "deleted", "deleted_at": datetime.utcnow()}})
                    results.append({"username": item.username, "action": "delete", "ok": True})
                elif item.action == "set_role":
                    if not item.value:
                        raise ValueError("Missing role value")
                    DB["users"].update_one({"username": item.username}, {"$set": {"role": item.value, "updated_at": datetime.utcnow()}})
                    results.append({"username": item.username, "action": "set_role", "ok": True, "role": item.value})
                else:
                    results.append({"username": item.username, "action": item.action, "ok": False, "error": "unsupported action"})
            except Exception as ie:
                results.append({"username": item.username, "action": item.action, "ok": False, "error": str(ie)})

        # Log bulk action
        DB["admin_actions"].insert_one({
            "admin_username": acting_admin,
            "action": "bulk_user_actions",
            "items": [i.model_dump() for i in request.items],
            "timestamp": datetime.utcnow()
        })

        return {"results": results}
    except Exception as e:
        logger.error(f"Bulk user actions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs")
async def get_audit_logs(
    username: Optional[str] = None,
    category: Optional[str] = None,
    days: int = 30,
    limit: int = 100,
    skip: int = 0,
    admin_user = Depends(verify_admin)
):
    """Query admin actions / audit events. Uses `admin_actions` collection by default."""
    try:
        query = {}
        if username:
            query["target_user"] = username
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query["timestamp"] = {"$gte": since}

        # Apply category filter in the MongoDB query when possible,
        # so skip/limit paginate the correct result set.
        if category:
            from app.utils.audit_log import categorize_audit_action as _cat
            # Pre-filter by known action keywords that map to each category
            category_action_patterns = {
                "auth": {"$regex": "login|session|sign.in", "$options": "i"},
                "security": {"$regex": "password|2fa|security.alert|encrypt", "$options": "i"},
                "account": {"$regex": "profile|account|api.key|billing", "$options": "i"},
            }
            if category in category_action_patterns:
                query["action"] = category_action_patterns[category]

        cursor = DB["admin_actions"].find(query).sort("timestamp", -1).skip(skip).limit(limit)
        entries = list(cursor)

        # Normalize, categorize, and clean _id for JSON safety
        for e in entries:
            e["category"] = categorize_audit_action(e.get("action", ""))
            e["id"] = str(e.pop("_id", ""))
            if isinstance(e.get("timestamp"), datetime):
                e["timestamp"] = e["timestamp"].isoformat()

        # Post-filter by category for the "other" bucket or edge cases
        # not captured by the regex pre-filter
        if category:
            entries = [e for e in entries if e.get("category") == category]

        # Dedupe similar entries
        entries = dedupe_audit_entries(entries, window_minutes=30)

        # Get total count for the filtered query (before skip/limit)
        total_count = DB["admin_actions"].count_documents(query)

        return {"total": total_count, "entries": entries}
    except Exception as e:
        logger.error(f"Audit logs query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs/export")
async def export_audit_logs(
    username: Optional[str] = None,
    days: int = 30,
    format: str = "csv",
    admin_user = Depends(verify_admin)
):
    """Export audit logs as CSV (simple implementation)."""
    try:
        query = {}
        if username:
            query["target_user"] = username
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query["timestamp"] = {"$gte": since}

        cursor = DB["admin_actions"].find(query).sort("timestamp", -1)
        rows = []
        for e in cursor:
            rows.append({
                "timestamp": e.get("timestamp").isoformat() if isinstance(e.get("timestamp"), datetime) else str(e.get("timestamp")),
                "admin_username": e.get("admin_username"),
                "action": e.get("action"),
                "target_user": e.get("target_user", ""),
                "details": str(e.get("items", e.get("changes", "")))
            })

        if format.lower() != "csv":
            raise HTTPException(status_code=400, detail="Only csv export supported")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["timestamp", "admin_username", "action", "target_user", "details"]) 
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

        content = output.getvalue()
        headers = {"Content-Disposition": f"attachment; filename=admin_audit_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
        return Response(content=content, media_type="text/csv", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export audit logs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    admin_user: dict = Depends(verify_admin)
):
    """
    Get recent platform activity.
    Requires admin role.
    """
    try:
        activities = []
        
        # Recent user registrations
        recent_users = list(DB["users"].find({}, {"username": 1, "email": 1, "created_at": 1})
                           .sort("created_at", -1).limit(5))
        for user in recent_users:
            if "username" in user:  # Safety check
                activities.append({
                    "type": "user_registration",
                    "description": f"New user registered: {user['username']}",
                    "timestamp": user.get("created_at", datetime.utcnow()),
                    "user": user["username"]
                })
        
        # Recent VM assignments
        recent_vms = list(DB["vm_assignments"].find({}, {"username": 1, "vm_name": 1, "timestamp": 1})
                         .sort("timestamp", -1).limit(5))
        for vm in recent_vms:
            if "username" in vm and "vm_name" in vm:  # Safety check
                activities.append({
                    "type": "vm_created",
                    "description": f"{vm['username']} created VM: {vm['vm_name']}",
                    "timestamp": vm.get("timestamp", datetime.utcnow()),
                    "user": vm["username"]
                })
        
        # Recent payments
        recent_payments = list(DB["payments"].find({}, {"username": 1, "amount": 1, "status": 1, "created_at": 1})
                              .sort("created_at", -1).limit(5))
        for payment in recent_payments:
            if "username" in payment and "amount" in payment:  # Safety check
                activities.append({
                    "type": "payment",
                    "description": f"{payment['username']} made payment: ₹{payment['amount']} ({payment.get('status', 'unknown')})",
                    "timestamp": payment.get("created_at", datetime.utcnow()),
                    "user": payment["username"]
                })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        logger.info(f"Admin activity: Returning {len(activities)} activities")
        
        return {"activities": activities[:limit]}
    
    except Exception as e:
        logger.error(f"Admin activity error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity: {str(e)}")


@router.get("/system-health")
async def get_system_health(admin_user: dict = Depends(verify_admin)):
    """
    Get system health metrics.
    Requires admin role.
    """
    try:
        # Database connection check
        db_healthy = True
        try:
            DB["users"].find_one()
        except:
            db_healthy = False
        
        # Get database sizes
        stats = DB.command("dbStats")
        
        from app.ops.diagnostics import platform_diagnostics_snapshot

        health_data = {
            "database": {
                "healthy": db_healthy,
                "size_mb": round(stats.get("dataSize", 0) / 1024 / 1024, 2),
                "collections": stats.get("collections", 0)
            },
            "collections": {
                "users": DB["users"].count_documents({}),
                "vm_assignments": DB["vm_assignments"].count_documents({}),
                "files": DB["files"].count_documents({}),
                "payments": DB["payments"].count_documents({})
            },
            "platform": platform_diagnostics_snapshot(),
            "timestamp": datetime.utcnow()
        }
        
        logger.info(f"Admin system health: Database healthy: {db_healthy}")
        
        return health_data
    
    except Exception as e:
        logger.error(f"Admin system health error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch system health: {str(e)}")


@router.get("/analytics")
async def get_analytics(admin_user = Depends(verify_admin)):
    """
    Get platform analytics and metrics.
    Requires admin role.
    """
    try:
        # Revenue trends (last 6 months)
        revenue_trends = []
        for i in range(6, 0, -1):
            month_start = datetime.utcnow() - timedelta(days=30*i)
            month_end = datetime.utcnow() - timedelta(days=30*(i-1))
            
            revenue_pipeline = [
                {"$match": {
                    "status": "success",
                    "created_at": {"$gte": month_start, "$lt": month_end}
                }},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            result = list(DB["payments"].aggregate(revenue_pipeline))
            revenue = result[0]["total"] if result and len(result) > 0 else 0
            
            revenue_trends.append({
                "month": month_start.strftime("%b %Y"),
                "revenue": revenue
            })
        
        # User growth (last 6 months)
        user_growth = []
        for i in range(6, 0, -1):
            month_start = datetime.utcnow() - timedelta(days=30*i)
            month_end = datetime.utcnow() - timedelta(days=30*(i-1))
            
            new_users = DB["users"].count_documents({
                "created_at": {"$gte": month_start, "$lt": month_end}
            })
            
            user_growth.append({
                "month": month_start.strftime("%b %Y"),
                "new_users": new_users
            })
        
        # VM usage trends
        vm_usage = []
        for i in range(6, 0, -1):
            month_start = datetime.utcnow() - timedelta(days=30*i)
            month_end = datetime.utcnow() - timedelta(days=30*(i-1))
            
            vm_count = DB["vm_assignments"].count_documents({
                "timestamp": {"$gte": month_start, "$lt": month_end}
            })
            
            vm_usage.append({
                "month": month_start.strftime("%b %Y"),
                "vms_created": vm_count
            })
        
        # Plan distribution
        plan_pipeline = [
            {"$group": {"_id": "$plan_id", "count": {"$sum": 1}}}
        ]
        plan_results = list(DB["users"].aggregate(plan_pipeline))
        plan_distribution = {
            item["_id"] or "free": item["count"] for item in plan_results
        }
        
        # Top users by spending
        top_spenders_pipeline = [
            {"$match": {"status": "success"}},
            {"$group": {"_id": "$username", "total_spent": {"$sum": "$amount"}}},
            {"$sort": {"total_spent": -1}},
            {"$limit": 10}
        ]
        top_spenders = list(DB["payments"].aggregate(top_spenders_pipeline))
        
        logger.info(f"Admin analytics generated")
        
        return {
            "revenue_trends": revenue_trends,
            "user_growth": user_growth,
            "vm_usage": vm_usage,
            "plan_distribution": plan_distribution,
            "top_spenders": top_spenders
        }
    
    except Exception as e:
        logger.error(f"Admin analytics error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.get("/payments")
async def get_payments(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    admin_user = Depends(verify_admin)
):
    """
    Get all payment transactions with filters.
    Requires admin role.
    """
    try:
        # Build query
        query = {}
        if status:
            query["status"] = status
        
        # Get payments
        payments_cursor = DB["payments"].find(query).sort("created_at", -1).skip(skip).limit(limit)
        payments = []
        
        for payment in payments_cursor:
            payments.append({
                "payment_id": str(payment.get("_id")),
                "username": payment.get("username"),
                "plan_id": payment.get("plan_id"),
                "amount": payment.get("amount"),
                "currency": payment.get("currency", "INR"),
                "status": payment.get("status"),
                "payment_method": payment.get("payment_method", "razorpay"),
                "razorpay_order_id": payment.get("razorpay_order_id"),
                "razorpay_payment_id": payment.get("razorpay_payment_id"),
                "created_at": payment.get("created_at"),
                "billing_cycle": payment.get("billing_cycle")
            })
        
        # Get total count and revenue
        total_count = DB["payments"].count_documents(query)
        
        revenue_pipeline = [
            {"$match": {**query, "status": "success"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        revenue_result = list(DB["payments"].aggregate(revenue_pipeline))
        total_revenue = revenue_result[0]["total"] if revenue_result and len(revenue_result) > 0 else 0
        
        logger.info(f"Admin payments: Returning {len(payments)} payments (total: {total_count})")
        
        return {
            "payments": payments,
            "total": total_count,
            "total_revenue": total_revenue,
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"Admin payments error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch payments: {str(e)}")


@router.get("/settings")
async def get_admin_settings(admin_user = Depends(verify_admin)):
    """
    Get platform settings and configuration.
    Requires admin role.
    """
    try:
        # Get or create platform settings
        settings = DB["platform_settings"].find_one({"_id": "platform_config"})
        
        if not settings:
            # Create default settings
            settings = {
                "_id": "platform_config",
                "platform_name": "Zenith Cloud",
                "maintenance_mode": False,
                "allow_new_registrations": True,
                "default_vm_limit": 2,
                "default_storage_gb": 10,
                "email_notifications_enabled": True,
                "require_email_verification": False,
                "session_timeout_hours": 24,
                "max_login_attempts": 5,
                "updated_at": datetime.utcnow()
            }
            DB["platform_settings"].insert_one(settings)
        
        # Get statistics
        total_users = DB["users"].count_documents({})
        active_subscriptions = DB["subscriptions"].count_documents({"status": "active"})
        total_revenue = 0
        revenue_result = list(DB["payments"].aggregate([
            {"$match": {"status": "success"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]))
        if revenue_result and len(revenue_result) > 0:
            total_revenue = revenue_result[0]["total"]
        
        logger.info(f"Admin settings retrieved")
        
        return {
            "settings": {
                "platform_name": settings.get("platform_name", "Zenith Cloud"),
                "maintenance_mode": settings.get("maintenance_mode", False),
                "allow_new_registrations": settings.get("allow_new_registrations", True),
                "default_vm_limit": settings.get("default_vm_limit", 2),
                "default_storage_gb": settings.get("default_storage_gb", 10),
                "email_notifications_enabled": settings.get("email_notifications_enabled", True),
                "require_email_verification": settings.get("require_email_verification", False),
                "sso_google_enabled": settings.get("sso_google_enabled", False),
                "sso_oidc_enabled": settings.get("sso_oidc_enabled", False),
                "sso_oidc_issuer": settings.get("sso_oidc_issuer", ""),
                "sso_oidc_display_name": settings.get("sso_oidc_display_name", "Enterprise SSO"),
                "session_timeout_hours": settings.get("session_timeout_hours", 24),
                "max_login_attempts": settings.get("max_login_attempts", 5)
            },
            "statistics": {
                "total_users": total_users,
                "active_subscriptions": active_subscriptions,
                "total_revenue": total_revenue
            }
        }
    
    except Exception as e:
        logger.error(f"Admin settings error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch settings: {str(e)}")


class PlatformSettings(BaseModel):
    platform_name: Optional[str] = None
    maintenance_mode: Optional[bool] = None
    allow_new_registrations: Optional[bool] = None
    default_vm_limit: Optional[int] = None
    default_storage_gb: Optional[int] = None
    email_notifications_enabled: Optional[bool] = None
    require_email_verification: Optional[bool] = None
    sso_google_enabled: Optional[bool] = None
    sso_oidc_enabled: Optional[bool] = None
    sso_oidc_issuer: Optional[str] = None
    sso_oidc_display_name: Optional[str] = None
    session_timeout_hours: Optional[int] = None
    max_login_attempts: Optional[int] = None


@router.put("/settings")
async def update_admin_settings(
    settings_update: PlatformSettings,
    admin_user = Depends(verify_admin)
):
    """
    Update platform settings.
    Requires admin role.
    """
    try:
        # Build update dict (only include provided fields)
        update_data = {}
        if settings_update.platform_name is not None:
            update_data["platform_name"] = settings_update.platform_name
        if settings_update.maintenance_mode is not None:
            update_data["maintenance_mode"] = settings_update.maintenance_mode
        if settings_update.allow_new_registrations is not None:
            update_data["allow_new_registrations"] = settings_update.allow_new_registrations
        if settings_update.default_vm_limit is not None:
            update_data["default_vm_limit"] = settings_update.default_vm_limit
        if settings_update.default_storage_gb is not None:
            update_data["default_storage_gb"] = settings_update.default_storage_gb
        if settings_update.email_notifications_enabled is not None:
            update_data["email_notifications_enabled"] = settings_update.email_notifications_enabled
        if settings_update.require_email_verification is not None:
            update_data["require_email_verification"] = settings_update.require_email_verification
        if settings_update.sso_google_enabled is not None:
            update_data["sso_google_enabled"] = settings_update.sso_google_enabled
        if settings_update.sso_oidc_enabled is not None:
            update_data["sso_oidc_enabled"] = settings_update.sso_oidc_enabled
        if settings_update.sso_oidc_issuer is not None:
            update_data["sso_oidc_issuer"] = settings_update.sso_oidc_issuer
        if settings_update.sso_oidc_display_name is not None:
            update_data["sso_oidc_display_name"] = settings_update.sso_oidc_display_name
        if settings_update.session_timeout_hours is not None:
            update_data["session_timeout_hours"] = settings_update.session_timeout_hours
        if settings_update.max_login_attempts is not None:
            update_data["max_login_attempts"] = settings_update.max_login_attempts
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Update settings
        DB["platform_settings"].update_one(
            {"_id": "platform_config"},
            {"$set": update_data},
            upsert=True
        )
        
        # Log the action
        DB["admin_actions"].insert_one({
            "admin_username": admin_user.username,
            "action": "update_platform_settings",
            "changes": update_data,
            "timestamp": datetime.utcnow()
        })
        
        logger.info(f"Admin settings updated by {admin_user.username}")
        
        return {"success": True, "message": "Platform settings updated successfully"}
    
    except Exception as e:
        logger.error(f"Admin settings update error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
