# =============================================================================
# MODULE: users/routes_settings.py  (296 lines)
# PURPOSE: User preferences persistence — saves currency, timezone, date format,
#          notification toggles, language preference to MongoDB
# READS FROM:  users collection (preferences sub-document)
# WRITES TO:   users collection
# MOUNTED AT:  /api/settings → GET preferences, POST preferences
# CALLED BY:   SettingsPage.jsx, PreferencesContext.jsx (loads on login)
# DO NOT:
#   - Add theme to this endpoint — theme is handled by ThemeContext and CSS class on <html>
#   - Rename preference field keys — PreferencesContext.jsx destructures exact field names
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from ..users.routes_users import get_current_user
from ..users.user_model import User
from ..database.mongo_client import get_database
import secrets

router = APIRouter(prefix="/settings", tags=["Settings"])
DB = get_database()


class NotificationSettings(BaseModel):
    email_notifications: bool = True
    budget_alerts: bool = True
    security_alerts: bool = True
    weekly_reports: bool = False
    maintenance_updates: bool = True


class PreferencesSettings(BaseModel):
    theme: str = "dark"
    language: str = "en"
    timezone: str = "UTC-5"
    date_format: str = "MM/DD/YYYY"
    currency: str = "USD"
    # Infrastructure: boto3 (fast, Render-friendly) or terraform (full IaC + drift)
    provision_engine: Literal["boto3", "terraform"] = "boto3"

    @field_validator("provision_engine", mode="before")
    @classmethod
    def _normalize_provision_engine(cls, value: object) -> str:
        if value is None:
            return "boto3"
        v = str(value).lower().strip()
        if v not in ("boto3", "terraform"):
            raise ValueError("provision_engine must be 'boto3' or 'terraform'")
        return v


class BillingSettings(BaseModel):
    auto_renew: bool = True
    payment_method: Optional[str] = None


class SettingsResponse(BaseModel):
    notifications: NotificationSettings
    preferences: PreferencesSettings
    billing: BillingSettings


class APIKeyResponse(BaseModel):
    key_id: str
    key_preview: str
    created_at: datetime
    last_used: Optional[datetime] = None


@router.get("/", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get all user settings"""
    try:
        users_collection = DB["users"]
        user = users_collection.find_one({"username": current_user.username})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        settings = user.get("settings", {})
        
        return SettingsResponse(
            notifications=NotificationSettings(**settings.get("notifications", {})),
            preferences=PreferencesSettings(**settings.get("preferences", {})),
            billing=BillingSettings(**settings.get("billing", {}))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch settings: {str(e)}")


@router.put("/notifications")
async def update_notifications(
    notifications: NotificationSettings,
    current_user: User = Depends(get_current_user)
):
    """Update notification settings"""
    try:
        users_collection = DB["users"]
        
        result = users_collection.update_one(
            {"username": current_user.username},
            {
                "$set": {
                    "settings.notifications": notifications.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            # Create settings if doesn't exist
            users_collection.update_one(
                {"username": current_user.username},
                {
                    "$set": {
                        "settings": {"notifications": notifications.model_dump()},
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        
        return {"success": True, "message": "Notification settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update notifications: {str(e)}")


VALID_THEMES = frozenset({"dark", "light", "auto"})


@router.put("/preferences")
async def update_preferences(
    preferences: PreferencesSettings,
    current_user: User = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        if preferences.theme not in VALID_THEMES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid theme. Must be one of: {', '.join(sorted(VALID_THEMES))}",
            )

        users_collection = DB["users"]
        
        users_collection.update_one(
            {"username": current_user.username},
            {
                "$set": {
                    "settings.preferences": preferences.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"success": True, "message": "Preferences updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.put("/billing")
async def update_billing(
    billing: BillingSettings,
    current_user: User = Depends(get_current_user)
):
    """Update billing settings"""
    try:
        users_collection = DB["users"]
        
        users_collection.update_one(
            {"username": current_user.username},
            {
                "$set": {
                    "settings.billing": billing.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"success": True, "message": "Billing settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update billing: {str(e)}")


@router.get("/api-keys")
async def get_api_keys(current_user: User = Depends(get_current_user)):
    """Get user's API keys"""
    try:
        api_keys_collection = DB["api_keys"]
        keys = list(api_keys_collection.find(
            {"username": current_user.username, "revoked": {"$ne": True}},
            {"_id": 0}
        ))
        
        # Mask the keys for security
        for key in keys:
            full_key = key.get("key", "")
            key["key_preview"] = f"{full_key[:8]}****************************{full_key[-6:]}"
            del key["key"]
        
        return {"success": True, "keys": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch API keys: {str(e)}")


@router.post("/api-keys")
async def generate_api_key(current_user: User = Depends(get_current_user)):
    """Generate a new API key"""
    try:
        # Generate secure API key
        api_key = f"sk-prod-{secrets.token_urlsafe(32)}"
        key_id = secrets.token_hex(8)
        
        api_keys_collection = DB["api_keys"]
        
        key_data = {
            "key_id": key_id,
            "key": api_key,
            "username": current_user.username,
            "created_at": datetime.utcnow(),
            "last_used": None,
            "revoked": False
        }
        
        api_keys_collection.insert_one(key_data)
        
        # Mask the key in response (show full key only once)
        return {
            "success": True,
            "message": "API key generated successfully",
            "key": api_key,
            "key_id": key_id,
            "note": "Save this key securely. You won't be able to see it again."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate API key: {str(e)}")


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, current_user: User = Depends(get_current_user)):
    """Revoke an API key"""
    try:
        api_keys_collection = DB["api_keys"]
        
        result = api_keys_collection.update_one(
            {
                "key_id": key_id,
                "username": current_user.username
            },
            {
                "$set": {
                    "revoked": True,
                    "revoked_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return {"success": True, "message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke API key: {str(e)}")


@router.put("/payment-method")
async def update_payment_method(
    payment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update payment method"""
    try:
        # TODO: Integrate with payment gateway (Stripe, PayPal, etc.)
        users_collection = DB["users"]
        
        # For now, just store a masked version
        masked_method = f"Credit Card ****{payment_data.get('last_four', '0000')}"
        
        users_collection.update_one(
            {"username": current_user.username},
            {
                "$set": {
                    "settings.billing.payment_method": masked_method,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"success": True, "message": "Payment method updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update payment method: {str(e)}")


@router.get("/preferences-summary")
async def get_preferences_summary(current_user: User = Depends(get_current_user)):
    """
    Lightweight endpoint returning just notification preferences.
    Designed for backend services to check before sending emails.
    """
    try:
        users_collection = DB["users"]
        user = users_collection.find_one(
            {"username": current_user.username},
            {"settings.notifications": 1, "_id": 0}
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        notif_settings = user.get("settings", {}).get("notifications", {})

        return {
            "username": current_user.username,
            "notifications": NotificationSettings(**notif_settings).model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch preferences summary: {str(e)}")

