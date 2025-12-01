from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
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
from app.auth.auth_utils import get_password_hash, verify_password, mark_2fa_unverified
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.utils.responses import StandardResponse, ErrorResponses

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

@router.post("/register", status_code=201)
@limiter.limit("3/minute")  # Max 3 registrations per minute per IP
def register_user_route(request: Request, user: UserCreate, db: Collection = Depends(get_users_collection)):
    logger.info(f"Registration attempt for username: {user.username}")
    
    if db.find_one({"username": user.username}):
        logger.warning(f"Registration failed: Username '{user.username}' already exists")
        raise ErrorResponses.conflict(f"Username '{user.username}' is already taken")
    
    try:
        hashed_password = get_password_hash(user.password)
        user_in_db = UserInDB(**user.model_dump(), hashed_password=hashed_password)
        db.insert_one(user_in_db.model_dump())
        
        logger.info(f"User '{user.username}' registered successfully")
        return StandardResponse.success(
            data={"username": user.username},
            message=f"User {user.username} registered successfully",
            status_code=201
        )
    except Exception as e:
        logger.error(f"Registration error for '{user.username}': {str(e)}")
        raise ErrorResponses.internal_error("Failed to create user account")

@router.post("/token", response_model=Token)
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
def login_for_access_token_route(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Collection = Depends(get_users_collection)
):
    from app.database.mongo_client import get_database
    
    logger.info(f"Login attempt for username: {form_data.username}")
    
    user_dict = db.find_one({"username": form_data.username})
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise ErrorResponses.unauthorized("Incorrect username or password")
    
    user_in_db = UserInDB(**user_dict)

    # --- NEW LINE ADDED ---
    # After successful password verification, reset the 2FA verified flag.
    # This ensures the user must provide a new 2FA code to access protected
    # resources during this new session.
    mark_2fa_unverified(user_in_db.username)
    
    try:
        # Create session entry
        DB = get_database()
        sessions_collection = DB["sessions"]
        from uuid import uuid4
        
        session_id = str(uuid4())
        sessions_collection.insert_one({
            "_id": session_id,
            "username": user_in_db.username,
            "device": "Unknown Device",  # TODO: Parse User-Agent header
            "location": "Unknown Location",  # TODO: GeoIP lookup
            "ip_address": "0.0.0.0",  # TODO: Extract from request
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "is_current": True
        })
        
        # Log activity
        activity_collection = DB["activity_log"]
        activity_collection.insert_one({
            "username": user_in_db.username,
            "action": "Successful Login",
            "description": "User logged in successfully",
            "timestamp": datetime.utcnow(),
            "ip": "0.0.0.0"  # TODO: Extract from request
        })
        
        access_token = create_access_token(data={"sub": user_in_db.username})
        logger.info(f"User '{form_data.username}' logged in successfully")
        return Token(access_token=access_token, token_type="bearer")
    except Exception as e:
        logger.error(f"Login error for '{form_data.username}': {str(e)}")
        raise ErrorResponses.internal_error("Login failed. Please try again.")
    # Log activity
    activity_collection = DB["activity_log"]
    activity_collection.insert_one({
        "username": user_in_db.username,
        "action": "Successful Login",
        "description": "User logged in successfully",
        "timestamp": datetime.utcnow(),
        "ip": "0.0.0.0"  # TODO: Extract from request
    })
    
    access_token = create_access_token(data={"sub": user_in_db.username})
    return Token(access_token=access_token, token_type="bearer")