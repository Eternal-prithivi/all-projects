# backend/app/auth/auth_service.py

from . import auth_utils
from ..users.user_model import UserCreate, UserInDB
from pymongo.collection import Collection

def register_user(user: UserCreate, users_collection: Collection) -> UserInDB:
    """
    Registers a new user in the MongoDB database.
    Accepts the collection as a parameter.
    """
    # --- DEBUGGING STEP ---
    print("\n--- Inside register_user service ---")
    print(f"Is users_collection available? {users_collection is not None}")

    if users_collection.find_one({"username": user.username}):
        print(f"DEBUG: User '{user.username}' already exists.")
        return None
    
    hashed_password = auth_utils.get_password_hash(user.password)
    
    user_in_db = UserInDB(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    print(f"DEBUG: Attempting to insert document: {user_in_db.model_dump()}")
    
    # Insert the new user into the 'users' collection
    result = users_collection.insert_one(user_in_db.model_dump())
    
    print(f"DEBUG: Insert result acknowledged: {result.acknowledged}")
    print(f"DEBUG: Inserted document ID: {result.inserted_id}")
    print("--- End of register_user service ---\n")
    
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

    user_in_db = UserInDB(**user_dict)

    # Verify the password
    if not auth_utils.verify_password(password, user_in_db.hashed_password):
        return None

    return user_in_db
