"""
User Profile Management Routes
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from ..users.routes_users import get_current_user
from ..users.user_model import User
from ..database.mongo_client import get_database
from passlib.context import CryptContext

router = APIRouter(prefix="/profile", tags=["Profile"])
DB = get_database()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class ProfileResponse(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
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


class ActivityLogResponse(BaseModel):
    action: str
    description: str
    timestamp: datetime
    ip: Optional[str] = None


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
        
        # Verify current password
        if not pwd_context.verify(password_data.current_password, user.get("password", "")):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Hash new password
        hashed_password = pwd_context.hash(password_data.new_password)
        
        # Update password
        users_collection.update_one(
            {"username": current_user.username},
            {"$set": {
                "password": hashed_password,
                "updated_at": datetime.utcnow()
            }}
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
        
        # Build update data (only include non-None values)
        update_data = {k: v for k, v in profile_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        # Check if username or email already exists (if being updated)
        if "username" in update_data:
            existing_user = users_collection.find_one({
                "username": update_data["username"],
                "username": {"$ne": current_user.username}
            })
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")
        
        if "email" in update_data:
            existing_email = users_collection.find_one({
                "email": update_data["email"],
                "username": {"$ne": current_user.username}
            })
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already in use")
        
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
    """Upload profile picture"""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Validate file size (max 2MB)
        file_content = await file.read()
        if len(file_content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 2MB")
        
        # TODO: Upload to cloud storage (S3, GCS, Azure Blob)
        # For now, just store a placeholder URL
        picture_url = f"/uploads/profiles/{current_user.username}_{file.filename}"
        
        users_collection = DB["users"]
        users_collection.update_one(
            {"username": current_user.username},
            {"$set": {"profile_picture": picture_url, "updated_at": datetime.utcnow()}}
        )
        
        return {"success": True, "picture_url": picture_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload picture: {str(e)}")


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
            session_list.append(SessionResponse(
                id=str(session["_id"]),
                device=session.get("device", "Unknown Device"),
                location=session.get("location", "Unknown Location"),
                ip=session.get("ip_address", "0.0.0.0"),
                last_active=session.get("last_active", session.get("created_at", datetime.utcnow())),
                current=session.get("is_current", False)
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
        from bson import ObjectId
        
        sessions_collection = DB["sessions"]
        
        # Find the session
        session = sessions_collection.find_one({"_id": ObjectId(session_id)})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify session belongs to current user
        if session.get("username") != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized to terminate this session")
        
        # Prevent terminating current session
        if session.get("is_current"):
            raise HTTPException(status_code=400, detail="Cannot terminate current session. Please logout instead.")
        
        # Delete the session
        sessions_collection.delete_one({"_id": ObjectId(session_id)})
        
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


@router.get("/activity", response_model=List[ActivityLogResponse])
async def get_activity_log(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Get recent activity log for the current user"""
    try:
        activity_collection = DB["activity_log"]
        
        # Find recent activities for the user
        activities = list(
            activity_collection.find({"username": current_user.username})
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Map to response model
        activity_list = []
        for activity in activities:
            activity_list.append(ActivityLogResponse(
                action=activity.get("action", "Unknown Action"),
                description=activity.get("description", ""),
                timestamp=activity.get("timestamp", datetime.utcnow()),
                ip=activity.get("ip")
            ))
        
        return activity_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity log: {str(e)}")
