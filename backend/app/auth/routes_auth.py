# =============================================================================
# MODULE: routes_auth.py  (126 lines)
# PURPOSE: Registration + login — bcrypt password hash, JWT token creation,
#          2FA flag reset on login, session tracking, activity log
# READS FROM:  users collection, sessions collection
# WRITES TO:   users, sessions, activity_log collections
# DEPENDS ON:  auth_utils (get_password_hash, verify_password, mark_2fa_unverified)
#              slowapi rate limiter (3/min register, 5/min login)
# MOUNTED AT:  /api/auth (and legacy /auth alias) → /register, /token
# DO NOT:
#   - Remove mark_2fa_unverified() call on login — 2FA re-verify required per session
#   - Remove rate limiter decorators — prevents brute force attacks
#   - Apply registration password strength rules to the login endpoint
# =============================================================================
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pymongo.collection import Collection
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

# Corrected imports with 'app.' prefix
from app.users.user_model import Token, UserCreate, UserInDB
from app.database.mongo_client import get_users_collection
# --- MODIFIED LINE ---
# Import the new function to reset 2FA status on login
from app.auth.auth_utils import get_password_hash, verify_password, mark_2fa_unverified, get_current_user_optional
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.utils.responses import StandardResponse, ErrorResponses
from app.contact.email_service import EmailService
from app.trust.signup_guards import email_verification_required
from app.trust.signup_notify import notify_new_user_signup

# Set up logger
logger = setup_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# --- MODIFIED LINE ---
# Removed the prefix="/auth" as it's already defined in main.py
router = APIRouter(tags=["Authentication"])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def _auth_token_response(access_token: str, refresh_token: str) -> JSONResponse:
    from app.auth.cookie_auth import attach_auth_cookies, legacy_token_body_enabled

    body: dict = {"token_type": "bearer"}
    if legacy_token_body_enabled():
        body["access_token"] = access_token
        body["refresh_token"] = refresh_token
    response = JSONResponse(content=body)
    attach_auth_cookies(response, access_token, refresh_token)
    return response

@router.post("/register", status_code=201)
@limiter.limit("3/minute")  # Max 3 registrations per minute per IP
def register_user_route(request: Request, user: UserCreate, db: Collection = Depends(get_users_collection)):
    logger.info(f"Registration attempt for username: {user.username}")

    from app.auth.password_policy import validate_password_strength
    from app.trust.signup_guards import assert_email_allowed, verify_turnstile_token
    from app.utils.session_utils import get_client_ip

    validate_password_strength(user.password)
    assert_email_allowed(str(user.email))
    verify_turnstile_token(user.captcha_token, get_client_ip(request))
    
    if db.find_one({"username": user.username}):
        logger.warning(f"Registration failed: Username '{user.username}' already exists")
        raise ErrorResponses.conflict(f"Username '{user.username}' is already taken")
    
    try:
        hashed_password = get_password_hash(user.password)
        user_in_db = UserInDB(
            **user.model_dump(exclude={"password", "captcha_token"}),
            hashed_password=hashed_password,
        )
        doc = user_in_db.model_dump()
        require_verify = email_verification_required()
        if require_verify:
            token = secrets.token_urlsafe(32)
            doc["email_verified"] = False
            doc["email_verify_token"] = token
        else:
            doc["email_verified"] = True
        doc["created_at"] = datetime.utcnow()
        db.insert_one(doc)

        if require_verify:
            verify_link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
            from app.trust.signup_guards import is_test_signup_email

            if not is_test_signup_email(user.email):
                EmailService().send_verification_email(
                    to_email=user.email,
                    username=user.username,
                    verify_link=verify_link,
                )

        notify_new_user_signup(
            username=user.username,
            email=user.email,
            source="register",
        )

        logger.info(f"User '{user.username}' registered successfully")
        return StandardResponse.success(
            data={
                "username": user.username,
                "email_verification_required": require_verify,
            },
            message=(
                "Registration successful. Check your email to verify your account."
                if require_verify
                else f"User {user.username} registered successfully"
            ),
            status_code=201,
        )
    except Exception as e:
        logger.error(f"Registration error for '{user.username}': {str(e)}")
        raise ErrorResponses.internal_error("Failed to create user account")

@router.post("/token")
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
def login_for_access_token_route(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    captcha_token: Optional[str] = Form(None),
    db: Collection = Depends(get_users_collection),
):
    from app.database.mongo_client import get_database
    from app.trust.signup_guards import verify_turnstile_token
    from app.utils.session_utils import get_client_ip

    verify_turnstile_token(captcha_token, get_client_ip(request))

    username = (form_data.username or "").strip()
    logger.info("Login attempt for username: %r", username)

    user_dict = db.find_one({"username": username})
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        logger.warning("Failed login attempt for username: %r", username)
        raise ErrorResponses.unauthorized("Incorrect username or password")

    if user_dict.get("deleted") or user_dict.get("status") == "deleted":
        logger.warning("Login blocked for deleted account: %r", username)
        raise ErrorResponses.unauthorized("Incorrect username or password")

    if email_verification_required() and not user_dict.get("email_verified", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before signing in.",
        )

    user_in_db = UserInDB(**user_dict)

    # --- NEW LINE ADDED ---
    # After successful password verification, reset the 2FA verified flag.
    # This ensures the user must provide a new 2FA code to access protected
    # resources during this new session.
    mark_2fa_unverified(user_in_db.username)

    from app.utils.session_utils import (
        get_client_ip,
        parse_user_agent,
        resolve_geo_location,
        fingerprint_display,
    )
    from uuid import uuid4

    client_ip = get_client_ip(request)
    device_label = parse_user_agent(request.headers.get("user-agent"))
    device_fingerprint = (request.headers.get("x-device-fingerprint") or "").strip() or None
    # Short timeout — login must not block on a free external geo API (especially after cold start).
    location_label = resolve_geo_location(client_ip, timeout=0.8)

    try:
        DB = get_database()
        sessions_collection = DB["sessions"]

        sessions_collection.update_many(
            {"username": user_in_db.username},
            {"$set": {"is_current": False}},
        )

        session_id = str(uuid4())
        sessions_collection.insert_one({
            "_id": session_id,
            "username": user_in_db.username,
            "device": device_label,
            "location": location_label,
            "ip_address": client_ip,
            "device_fingerprint": device_fingerprint,
            "device_fingerprint_short": fingerprint_display(device_fingerprint),
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "is_current": True,
        })

        activity_collection = DB["activity_log"]
        activity_collection.insert_one({
            "username": user_in_db.username,
            "action": "Successful Login",
            "description": f"Signed in from {device_label}",
            "timestamp": datetime.utcnow(),
            "ip": client_ip,
        })
    except Exception as e:
        # Session/activity tracking must not block authentication
        logger.warning(
            "Login session tracking failed for '%s' (continuing): %s",
            form_data.username,
            e,
        )

    from app.auth.token_service import issue_token_pair

    access_token, refresh_token = issue_token_pair(user_in_db.username)
    logger.info(f"User '{form_data.username}' logged in successfully")
    return _auth_token_response(access_token, refresh_token)


@router.post("/refresh")
def refresh_access_token(request: Request, body: dict | None = None):
    from app.auth.cookie_auth import get_refresh_token_from_request
    from app.auth.token_service import rotate_refresh_token

    raw = (body or {}).get("refresh_token") or get_refresh_token_from_request(request) or ""
    access, refresh = rotate_refresh_token(raw)
    return _auth_token_response(access, refresh)


@router.post("/logout")
def logout_route(
    current_user: Optional[UserInDB] = Depends(get_current_user_optional),
):
    from app.auth.cookie_auth import clear_auth_cookies
    from app.auth.token_service import revoke_refresh_tokens

    response = JSONResponse(content={"success": True, "message": "Logged out"})
    clear_auth_cookies(response)
    if current_user is not None:
        revoke_refresh_tokens(current_user.username)
    return response


@router.post("/verify-email")
def verify_email_route(
    token: str = Query(..., min_length=8, max_length=128),
    db: Collection = Depends(get_users_collection),
):
    """
    Confirm email from registration link. Token is stored on user at signup when enabled.
    """
    user = db.find_one({"email_verify_token": token})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )
    db.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"email_verified": True, "email_verified_at": datetime.utcnow()},
            "$unset": {"email_verify_token": ""},
        },
    )
    logger.info("Email verified for user '%s'", user.get("username"))
    return StandardResponse.success(message="Email verified successfully. You can sign in now.")