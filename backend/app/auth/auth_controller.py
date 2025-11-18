# backend/app/auth/auth_controller.py

from fastapi.security import OAuth2PasswordRequestForm
from pymongo.collection import Collection
from . import auth_service, auth_utils
from ..users.user_model import UserCreate, Token
from fastapi import HTTPException, status

def register(user: UserCreate, db: Collection):
    """
    Controller logic to handle user registration.
    Accepts the db connection and passes it to the service.
    """
    db_user = auth_service.register_user(user, db)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    return {"message": f"User {db_user.username} registered successfully"}

def login_for_access_token(form_data: OAuth2PasswordRequestForm, db: Collection):
    """
    Controller logic to handle user login and token creation.
    Accepts the db connection and passes it to the service.
    """
    user = auth_service.authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_utils.create_access_token(
        data={"sub": user.username}
    )
    
    return Token(access_token=access_token, token_type="bearer")

