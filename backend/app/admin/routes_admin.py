"""
Admin routes for platform management.
Only accessible to users with admin role.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from ..database.mongo_client import get_database
from ..auth.auth_utils import get_current_user
from app.utils.logger import setup_logger

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
    
    try:
        result = DB["users"].update_one(
            {"username": username},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log the action
        DB["admin_actions"].insert_one({
            "admin_username": admin_user["username"],
            "action": "update_user_status",
            "target_user": username,
            "new_status": status,
            "timestamp": datetime.utcnow()
        })
        
        logger.info(f"Admin action: {admin_user['username']} updated {username} status to {status}")
        
        return {"success": True, "message": f"User {username} status updated to {status}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin action error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update user status: {str(e)}")


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
