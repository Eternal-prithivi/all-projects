from pymongo import MongoClient
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__) # Correct import

class MongoDB:
    def __init__(self):
        try:
            self.client = MongoClient(settings.MONGO_CONNECTION_STRING)
            self.db = self.client['CloudResourceOptimizationDB']
            print("✅ Successfully connected to MongoDB.")
        except Exception as e:
            print(f"❌ Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None

    def get_collection(self, collection_name: str):
        if self.db is not None:
            return self.db[collection_name]
        return None

mongodb_client = MongoDB()

def get_database():
    """Get database instance for VM management and other operations"""
    if mongodb_client.db is not None:
        return mongodb_client.db
    raise RuntimeError("Database not initialized. MongoDB connection failed.")

def get_users_collection():
    return mongodb_client.get_collection("users")
