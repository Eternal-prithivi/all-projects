from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    hashed_password: str
    role: str = Field(default="user")  # user or admin

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    captcha_token: Optional[str] = None

class UserInDB(User):
    # Pydantic model for users as they are stored in the database
    # Added fields for Two-Factor Authentication (2FA)
    two_fa_secret: Optional[str] = None
    two_fa_enabled: bool = Field(False)
    two_fa_verified: bool = Field(False)
    role: str = Field(default="user")  # user or admin
    email_verified: bool = Field(default=True)
    email_verify_token: Optional[str] = None
    google_id: Optional[str] = None
    sso_provider: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
