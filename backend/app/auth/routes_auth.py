from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.collection import Collection
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt

# Corrected imports with 'app.' prefix
from app.users.user_model import Token, UserCreate, UserInDB
from app.database.mongo_client import get_users_collection
# --- MODIFIED LINE ---
# Import the new function to reset 2FA status on login
from app.auth.auth_utils import get_password_hash, verify_password, mark_2fa_unverified
from app.utils.config import settings

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
def register_user_route(user: UserCreate, db: Collection = Depends(get_users_collection)):
    if db.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    user_in_db = UserInDB(**user.model_dump(), hashed_password=hashed_password)
    db.insert_one(user_in_db.model_dump())
    
    return {"message": f"User {user.username} registered successfully"}

@router.post("/token", response_model=Token)
def login_for_access_token_route(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Collection = Depends(get_users_collection)
):
    from app.database.mongo_client import get_database
    
    user_dict = db.find_one({"username": form_data.username})
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    user_in_db = UserInDB(**user_dict)

    # --- NEW LINE ADDED ---
    # After successful password verification, reset the 2FA verified flag.
    # This ensures the user must provide a new 2FA code to access protected
    # resources during this new session.
    mark_2fa_unverified(user_in_db.username)
    
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
    return Token(access_token=access_token, token_type="bearer")