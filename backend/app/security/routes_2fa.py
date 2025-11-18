import pyotp
import qrcode
import io
import base64
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.database.mongo_client import get_users_collection
from app.auth.auth_utils import get_current_user
# --- MODIFIED LINE ---
# Import the UserInDB model to correctly type-hint the current_user dependency
from app.users.user_model import UserInDB

# --- MODIFIED LINE ---
# Removed prefix (handled in main.py) and added a tag for consistency
router = APIRouter(tags=["2FA"])

# Request model
class Verify2FARequest(BaseModel):
    code: str

# Finalize Setup Request model
class Finalize2FARequest(BaseModel):
    code: str

# Check current 2FA status
@router.get("/status-2fa")
async def status_2fa(current_user: UserInDB = Depends(get_current_user)):
    """
    Returns the 2FA status for the current user.
    """
    # --- MODIFIED LINES ---
    # Changed from dictionary .get() to direct attribute access
    secret_exists = bool(current_user.two_fa_secret)
    enabled = bool(current_user.two_fa_enabled)
    verified = bool(current_user.two_fa_verified)
    return {
        "enabled": enabled,
        "verified": verified,
        "secret_exists": secret_exists,
    }

# Enable 2FA (first step: generate secret and QR code)
@router.post("/enable-2fa")
async def enable_2fa(current_user: UserInDB = Depends(get_current_user)):
    """
    Generates a new 2FA secret and a QR code for the user to scan.
    """
    users_col = get_users_collection()

    # --- MODIFIED LOGIC ---
    # Use the secret from the user object if it exists, otherwise create one.
    if current_user.two_fa_secret:
        secret = current_user.two_fa_secret
    else:
        secret = pyotp.random_base32()
        users_col.update_one(
            {"username": current_user.username},
            {
                "$set": {
                    "two_fa_secret": secret,
                    "two_fa_enabled": False,
                    "two_fa_verified": False,
                }
            },
        )
    
    # Generate provisioning URI for QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.username, issuer_name="ZenithApp"
    )

    # ... (QR code generation remains the same) ...
    qr = qrcode.QRCode(box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    qr_data_url = f"data:image/png;base64,{qr_base64}"

    return {"qr_code": qr_data_url, "message": "Scan QR code to finalize 2FA setup."}

# Finalize 2FA setup (second step: verify the token and enable 2FA)
@router.post("/finalize-2fa")
async def finalize_2fa(
    req: Finalize2FARequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Verifies the user's first 2FA code and enables 2FA for their account.
    """
    users_col = get_users_collection()
    
    # --- MODIFIED LOGIC ---
    # We need to fetch the user again here to get the un-verified secret
    user_in_db = users_col.find_one({"username": current_user.username})
    
    if not user_in_db or not user_in_db.get("two_fa_secret"):
        raise HTTPException(status_code=400, detail="2FA setup not initiated.")

    totp = pyotp.TOTP(user_in_db["two_fa_secret"])
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    users_col.update_one(
        {"username": current_user.username},
        {"$set": {"two_fa_enabled": True, "two_fa_verified": True}}
    )

    return {"verified": True, "message": "2FA successfully enabled."}

# Verify 2FA token for a given session
@router.post("/verify-2fa")
async def verify_2fa(
    req: Verify2FARequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Verifies a user's 2FA code for a specific session.
    """
    if not current_user.two_fa_secret:
        raise HTTPException(status_code=400, detail="2FA not set up")

    totp = pyotp.TOTP(current_user.two_fa_secret)
    if not totp.verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    users_col = get_users_collection()
    users_col.update_one(
        {"username": current_user.username},
        {"$set": {"two_fa_verified": True}}
    )

    return {"verified": True, "message": "2FA verified for this session."}

# Disable 2FA
@router.post("/disable-2fa")
async def disable_2fa(current_user: UserInDB = Depends(get_current_user)):
    """
    Disables 2FA for the user's account by removing the secret key.
    """
    users_col = get_users_collection()
    users_col.update_one(
        {"username": current_user.username},
        {"$unset": {"two_fa_secret": "", "two_fa_enabled": "", "two_fa_verified": ""}}
    )
    return {"message": "2FA has been disabled."}