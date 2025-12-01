from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from pymongo.collection import Collection
from pydantic import BaseModel, EmailStr

from app.users.user_model import User
from app.database.mongo_client import get_users_collection
from app.utils.config import settings

# Response model without hashed_password
class UserResponse(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"

# The prefix is now handled in main.py, so it's removed from here.
router = APIRouter(tags=["Users"])

# This helper function will expect a token in the request header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token") # Corrected tokenUrl to match full path

# This function decodes the token, finds the user in the database, and returns their data
def get_current_user(token: str = Depends(oauth2_scheme), db: Collection = Depends(get_users_collection)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return User(**user)

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    An endpoint that returns the details for the currently logged-in user.
    It's protected by the get_current_user dependency.
    """
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        role=current_user.role
    )
