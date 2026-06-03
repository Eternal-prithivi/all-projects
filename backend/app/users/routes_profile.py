# =============================================================================
# MODULE: routes_profile.py  (534 lines)
# PURPOSE: User profile CRUD — update display name/bio/avatar, change password,
#          session management (list/revoke), activity log, account deletion
# READS FROM:  users, sessions, activity_log collections
# WRITES TO:   users, sessions, activity_log collections
# DEPENDS ON:  auth_utils.get_current_user(), S3 for avatar uploads
# MOUNTED AT:  /api/profile → me, update, change-password, sessions,
#              activity-log, delete-account, avatar
# DO NOT:
#   - Allow password change without verifying the current password first
#   - Delete the last session (current session) via revoke — guard against it
#   - Return hashed_password in any profile response
# =============================================================================

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from ..users.routes_users import get_current_user
from ..users.user_model import User
from ..database.mongo_client import get_database
from app.auth.auth_utils import verify_password, get_password_hash
from app.auth.password_reset_service import normalize_phone_e164
from app.utils.audit_log import categorize_audit_action

router = APIRouter(prefix="/profile", tags=["Profile"])
DB = get_database()


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    recovery_phone: Optional[str] = None
    recovery_email: Optional[EmailStr] = None
    company: Optional[str] = None


class ProfileResponse(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    recovery_phone: Optional[str] = None
    recovery_email: Optional[str] = None
    company: Optional[str] = None
    role: str
    profile_picture: Optional[str] = None
    created_at: Optional[datetime] = None


class AccountStats(BaseModel):
    total_vms_created: int
    storage_used_tb: float
    total_spend: float
    member_since: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class SessionResponse(BaseModel):
    id: str
    device: str
    location: str
    ip: str
    last_active: datetime
    current: bool
    device_fingerprint_short: Optional[str] = None


class ActivityLogResponse(BaseModel):
    action: str
    description: str
    timestamp: datetime
    ip: Optional[str] = None
    category: str = "other"


class ActivityLogPageResponse(BaseModel):
    items: List[ActivityLogResponse]
    total: int
    limit: int
    skip: int
    has_more: bool
    period_days: int


class ActivitySummaryResponse(BaseModel):
    period_days: int
    total_events: int
    sign_ins: int
    security_events: int
    account_events: int
    recent: List[ActivityLogResponse]


@router.put("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user)
):
    """Change user's password"""
    try:
        users_collection = DB["users"]
        user = users_collection.find_one({"username": current_user.username})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        stored_hash = user.get("hashed_password") or user.get("password")
        if not stored_hash or not verify_password(password_data.current_password, stored_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        new_hashed = get_password_hash(password_data.new_password)

        users_collection.update_one(
            {"username": current_user.username},
            {"$set": {
                "hashed_password": new_hashed,
                "updated_at": datetime.utcnow()
            },
             "$unset": {"password": ""}}
        )
        
        # Log activity
        activity_collection = DB["activity_log"]
        activity_collection.insert_one({
            "username": current_user.username,
            "action": "Password Changed",
            "description": "User changed their password",
            "timestamp": datetime.utcnow()
        })
        
        return {"success": True, "message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")


@router.get("/me", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile information"""
    try:
        users_collection = DB["users"]
        user = users_collection.find_one({"username": current_user.username})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return ProfileResponse(
            username=user.get("username", ""),
            email=user.get("email", "user@example.com"),
            full_name=user.get("full_name", ""),
            phone=user.get("phone", ""),
            recovery_phone=user.get("recovery_phone", ""),
            recovery_email=user.get("recovery_email", ""),
            company=user.get("company", ""),
            role=user.get("role", "Admin"),
            profile_picture=user.get("profile_picture"),
            created_at=user.get("created_at")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")


@router.put("/me")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile information"""
    try:
        users_collection = DB["users"]
        
        raw = profile_data.model_dump(exclude_unset=True)
        update_data = {}
        for key, value in raw.items():
            if key in ("phone", "recovery_phone"):
                if value is None or (isinstance(value, str) and not value.strip()):
                    update_data[key] = ""
                    continue
                normalized = normalize_phone_e164(value.strip())
                if not normalized:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid {key.replace('_', ' ')}. Use international format, e.g. +919876543210",
                    )
                update_data[key] = normalized
                continue
            if key == "recovery_email" and isinstance(value, str) and not value.strip():
                update_data[key] = ""
                continue
            if value is not None:
                update_data[key] = value

        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        # Check uniqueness only when username/email actually change
        if "username" in update_data and update_data["username"] != current_user.username:
            existing_user = users_collection.find_one({"username": update_data["username"]})
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")

        if "email" in update_data:
            existing_email = users_collection.find_one({
                "email": update_data["email"],
                "username": {"$ne": current_user.username},
            })
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already in use")

        if update_data.get("recovery_email"):
            existing_recovery = users_collection.find_one({
                "recovery_email": update_data["recovery_email"],
                "username": {"$ne": current_user.username},
            })
            if existing_recovery:
                raise HTTPException(status_code=400, detail="Recovery email already in use")
        
        # Update user profile
        update_data["updated_at"] = datetime.utcnow()
        result = users_collection.update_one(
            {"username": current_user.username},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Profile not updated")
        
        # Log activity
        activity_collection = DB["activity_log"]
        activity_collection.insert_one({
            "username": current_user.username,
            "action": "Profile Updated",
            "description": f"User updated their profile ({', '.join(update_data.keys())})",
            "timestamp": datetime.utcnow()
        })
        
        return {"success": True, "message": "Profile updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.post("/picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Profile avatars are not yet stored in object storage (tri-cloud).
    Use Settings → display name until S3/GCS/Blob upload ships (Phase 27 backlog).
    """
    raise HTTPException(
        status_code=501,
        detail={
            "code": "not_implemented",
            "message": (
                "Profile picture upload is not available yet. "
                "Tri-cloud object storage for avatars is planned; use display name for now."
            ),
        },
    )


@router.delete("/picture")
async def remove_profile_picture(current_user: User = Depends(get_current_user)):
    """Remove profile picture"""
    try:
        users_collection = DB["users"]
        users_collection.update_one(
            {"username": current_user.username},
            {"$set": {"profile_picture": None, "updated_at": datetime.utcnow()}}
        )
        
        return {"success": True, "message": "Profile picture removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove picture: {str(e)}")


@router.get("/stats", response_model=AccountStats)
async def get_account_stats(current_user: User = Depends(get_current_user)):
    """Get user's account statistics"""
    try:
        users_collection = DB["users"]
        vm_assignments_collection = DB["vm_assignments"]
        files_collection = DB["files"]
        
        user = users_collection.find_one({"username": current_user.username})
        
        # Count total VMs created (including released ones)
        total_vms = vm_assignments_collection.count_documents({
            "username": current_user.username
        })
        
        # Calculate storage used
        user_files = list(files_collection.find({"username": current_user.username}))
        total_storage_bytes = sum(f.get("size", 0) for f in user_files)
        storage_tb = round(total_storage_bytes / (1024 ** 4), 2)  # Convert to TB
        
        # Calculate total spend (mock data for now)
        # TODO: Integrate with actual billing data
        total_spend = round(total_vms * 45.50 + storage_tb * 23.5, 2)
        
        # Member since
        created_at = user.get("created_at")
        if created_at:
            member_since = created_at.strftime("%B %Y")
        else:
            member_since = "Recent"
        
        return AccountStats(
            total_vms_created=total_vms,
            storage_used_tb=storage_tb,
            total_spend=total_spend,
            member_since=member_since
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.delete("/account")
async def delete_account(current_user: User = Depends(get_current_user)):
    """Delete user account (soft delete)"""
    try:
        users_collection = DB["users"]
        
        # Mark account as deleted instead of actually deleting
        users_collection.update_one(
            {"username": current_user.username},
            {"$set": {
                "deleted": True,
                "deleted_at": datetime.utcnow(),
                "status": "deleted"
            }}
        )
        
        # TODO: Release all VMs, delete files, clean up resources
        
        return {"success": True, "message": "Account deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


@router.get("/sessions", response_model=List[SessionResponse])
async def get_active_sessions(current_user: User = Depends(get_current_user)):
    """Get all active sessions for the current user"""
    try:
        sessions_collection = DB["sessions"]
        
        # Find all active sessions for the user
        sessions = list(sessions_collection.find({"username": current_user.username}))
        
        # Map to response model
        session_list = []
        for session in sessions:
            device = session.get("device") or "Web browser"
            if device in ("Unknown Device", "Unknown"):
                device = "Web browser"

            location = session.get("location") or "Local network"
            if location in ("Unknown Location", "Unknown"):
                location = "Local network"

            ip = session.get("ip_address") or session.get("ip") or "—"
            if ip in ("0.0.0.0", "Unknown"):
                ip = "—"

            session_list.append(SessionResponse(
                id=str(session["_id"]),
                device=device,
                location=location,
                ip=ip,
                last_active=session.get("last_active", session.get("created_at", datetime.utcnow())),
                current=session.get("is_current", False),
                device_fingerprint_short=session.get("device_fingerprint_short"),
            ))
        
        return session_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Terminate a specific session"""
    try:
        sessions_collection = DB["sessions"]

        session = sessions_collection.find_one({"_id": session_id})
        if not session:
            from bson import ObjectId
            try:
                session = sessions_collection.find_one({"_id": ObjectId(session_id)})
            except Exception:
                session = None

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify session belongs to current user
        if session.get("username") != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized to terminate this session")
        
        # Prevent terminating current session
        if session.get("is_current"):
            raise HTTPException(status_code=400, detail="Cannot terminate current session. Please logout instead.")
        
        # Delete the session
        sessions_collection.delete_one({"_id": session["_id"]})
        
        # Log activity
        activity_collection = DB["activity_log"]
        activity_collection.insert_one({
            "username": current_user.username,
            "action": "Session Terminated",
            "description": f"Terminated session from {session.get('device', 'Unknown Device')}",
            "timestamp": datetime.utcnow(),
            "ip": session.get("ip_address")
        })
        
        return {"success": True, "message": "Session terminated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to terminate session: {str(e)}")


def _map_activity_doc(activity: dict) -> ActivityLogResponse:
    action = activity.get("action", "Unknown Action")
    return ActivityLogResponse(
        action=action,
        description=activity.get("description", ""),
        timestamp=activity.get("timestamp", datetime.utcnow()),
        ip=activity.get("ip"),
        category=activity.get("category") or categorize_audit_action(action),
    )


@router.get("/activity/summary", response_model=ActivitySummaryResponse)
async def get_activity_summary(
    period_days: int = 30,
    current_user: User = Depends(get_current_user),
):
    """
    Compact summary for Security Settings — stats + last few notable events only.
    """
    from app.utils.audit_log import (
        build_activity_query,
        categorize_audit_action,
        dedupe_audit_entries,
    )

    try:
        period_days = max(7, min(period_days, 90))
        activity_collection = DB["activity_log"]
        query = build_activity_query(current_user.username, days=period_days)

        raw = list(activity_collection.find(query).sort("timestamp", -1).limit(200))
        deduped = dedupe_audit_entries(raw, window_minutes=30)

        sign_ins = sum(1 for e in deduped if categorize_audit_action(e.get("action", "")) == "auth")
        security_events = sum(
            1 for e in deduped if categorize_audit_action(e.get("action", "")) == "security"
        )
        account_events = sum(
            1 for e in deduped if categorize_audit_action(e.get("action", "")) == "account"
        )

        recent_docs = deduped[:3]
        return ActivitySummaryResponse(
            period_days=period_days,
            total_events=len(deduped),
            sign_ins=sign_ins,
            security_events=security_events,
            account_events=account_events,
            recent=[_map_activity_doc(a) for a in recent_docs],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity summary: {str(e)}")


@router.get("/activity", response_model=ActivityLogPageResponse)
async def get_activity_log(
    limit: int = 15,
    skip: int = 0,
    period_days: int = 30,
    category: str = "all",
    current_user: User = Depends(get_current_user),
):
    """
    Paginated security audit log (last 90 days max).
    Use /activity/summary on settings pages; use this for full history views.
    """
    from app.utils.audit_log import (
        build_activity_query,
        dedupe_audit_entries,
        filter_by_category,
    )

    try:
        limit = max(5, min(limit, 50))
        skip = max(0, skip)
        period_days = max(7, min(period_days, 90))

        activity_collection = DB["activity_log"]
        query = build_activity_query(current_user.username, days=period_days)

        raw = list(activity_collection.find(query).sort("timestamp", -1).limit(500))
        deduped = dedupe_audit_entries(raw, window_minutes=30)
        filtered = filter_by_category(deduped, category.lower())

        total = len(filtered)
        page_docs = filtered[skip : skip + limit]

        return ActivityLogPageResponse(
            items=[_map_activity_doc(a) for a in page_docs],
            total=total,
            limit=limit,
            skip=skip,
            has_more=(skip + limit) < total,
            period_days=period_days,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity log: {str(e)}")


@router.get("/activity/export")
async def export_activity_log_csv(
    period_days: int = 30,
    category: str = "all",
    current_user: User = Depends(get_current_user),
):
    """Export user activity / security audit log as CSV."""
    from app.utils.audit_log import build_activity_query, dedupe_audit_entries, filter_by_category

    try:
        period_days = max(7, min(period_days, 90))
        activity_collection = DB["activity_log"]
        query = build_activity_query(current_user.username, days=period_days)
        raw = list(activity_collection.find(query).sort("timestamp", -1).limit(2000))
        deduped = dedupe_audit_entries(raw, window_minutes=30)
        filtered = filter_by_category(deduped, category.lower())

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["timestamp", "action", "description", "category", "ip"],
        )
        writer.writeheader()
        for doc in filtered:
            action = doc.get("action", "")
            writer.writerow(
                {
                    "timestamp": (
                        doc.get("timestamp").isoformat()
                        if isinstance(doc.get("timestamp"), datetime)
                        else str(doc.get("timestamp", ""))
                    ),
                    "action": action,
                    "description": doc.get("description", ""),
                    "category": categorize_audit_action(action),
                    "ip": doc.get("ip", ""),
                }
            )

        filename = f"zenith_activity_{current_user.username}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export activity log: {str(e)}")
