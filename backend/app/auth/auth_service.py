# backend/app/auth/auth_service.py

from . import auth_utils
from ..users.user_model import UserCreate, UserInDB
from pymongo.collection import Collection
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

def register_user(user: UserCreate, users_collection: Collection) -> UserInDB:
    """
    Registers a new user in the MongoDB database.
    Accepts the collection as a parameter.
    """
    logger.debug(f"Register user attempt: {user.username}")

    if users_collection.find_one({"username": user.username}):
        logger.warning(f"User '{user.username}' already exists")
        return None
    
    hashed_password = auth_utils.get_password_hash(user.password)
    
    user_in_db = UserInDB(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    logger.debug(f"Inserting user document for: {user.username}")
    
    # Insert the new user into the 'users' collection
    result = users_collection.insert_one(user_in_db.model_dump())
    
    logger.info(f"User registered successfully: {user.username}")
    
    return user_in_db

def authenticate_user(username: str, password: str, users_collection: Collection) -> UserInDB | None:
    """
    Authenticates a user against the MongoDB database.
    Accepts the collection as a parameter.
    """
    # Find the user by username
    user_dict = users_collection.find_one({"username": username})
    if not user_dict:
        return None

    if user_dict.get("deleted") or user_dict.get("status") == "deleted":
        return None

    user_in_db = UserInDB(**user_dict)

    # Verify the password
    if not auth_utils.verify_password(password, user_in_db.hashed_password):
        return None

    return user_in_db
