"""
Temporary setup routes for initial configuration.
DELETE THESE AFTER SETUP IS COMPLETE!
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..database.mongo_client import get_database

router = APIRouter(prefix="/api/setup", tags=["Setup"])
DB = get_database()

@router.post("/make-admin/{username}")
async def make_user_admin(username: str, secret: str):
    """
    Make a user admin. For setup only!
    Use secret=dev123 for now.
    """
    # Simple security check
    if secret != "dev123":
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    result = DB["users"].update_one(
        {"username": username},
        {"$set": {"role": "admin", "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "message": f"User {username} is now an admin!",
        "note": "Please log out and log back in to see changes."
    }

@router.get("/check-admin/{username}")
async def check_admin_status(username: str):
    """Check if a user is admin"""
    user = DB["users"].find_one({"username": username})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": username,
        "role": user.get("role", "user"),
        "is_admin": user.get("role") == "admin"
    }
