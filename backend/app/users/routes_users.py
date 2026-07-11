from fastapi import APIRouter, Depends
from pymongo.collection import Collection
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.auth.auth_utils import get_current_user
from app.database.mongo_client import get_users_collection
from app.users.user_model import UserInDB

# Response model without hashed_password
class UserResponse(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"
    profile_picture: Optional[str] = None
    full_name: Optional[str] = None
    email_verified: bool = True

router = APIRouter(tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_user),
    db: Collection = Depends(get_users_collection),
):
    """Return the currently authenticated user (Bearer header or httpOnly cookie)."""
    user_doc = db.find_one({"username": current_user.username}) or {}
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        profile_picture=user_doc.get("profile_picture"),
        full_name=user_doc.get("full_name"),
        email_verified=bool(user_doc.get("email_verified", True)),
    )
