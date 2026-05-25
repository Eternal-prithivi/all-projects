# =============================================================================
# MODULE: mongo_client.py  (106 lines)
# PURPOSE: Singleton MongoDB connection — every route uses this to get collections
#   - mongodb_client.get_collection("name") — returns a pymongo Collection
#   - get_users_collection() / get_database() — FastAPI Depends() shortcuts
# DATABASE: CloudResourceOptimizationDB on MongoDB Atlas
# USED BY: Every route file in the project — this is the DB layer
# DO NOT:
#   - Create new MongoClient instances elsewhere — always use this singleton
#   - Change the database name ("CloudResourceOptimizationDB") — all code hard-wires it
#   - Add synchronous blocking calls in async route handlers without care
# =============================================================================
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
            self.ensure_indexes()
        except Exception as e:
            print(f"❌ Error connecting to MongoDB: {e}")
            self.client = None
            self.db = None

    def ensure_indexes(self) -> None:
        """
        Create essential indexes used across the app.

        This is a lightweight, idempotent operation that makes queries faster and
        prevents accidental duplicates (where appropriate).
        """
        if self.db is None:
            return

        try:
            # files: prevent duplicate metadata records per user+filename
            self._create_index_if_missing("files", [("owner_username", 1), ("filename", 1)], unique=True)
            self._create_index_if_missing("files", [("owner_username", 1), ("last_accessed_at", -1)])
            self._create_index_if_missing("files", [("storage_class", 1), ("last_accessed_at", -1)])
            self._create_index_if_missing("files", [("last_tier_change", -1)])

            # secure_files: fast lookups for security alerts and listing
            self._create_index_if_missing("secure_files", [("owner_username", 1), ("filename", 1)])
            self._create_index_if_missing("secure_files", [("owner_username", 1), ("is_sensitive", 1), ("is_encrypted", 1)])

            # sessions + activity log
            self._create_index_if_missing("sessions", [("username", 1), ("last_active", -1)])
            self._create_index_if_missing("activity_log", [("username", 1), ("timestamp", -1)])
            self._create_index_if_missing("password_reset_requests", [("token_hash", 1)])
            self._create_index_if_missing(
                "password_reset_requests",
                "expires_at", expireAfterSeconds=0
            )

            # Phase 5: ML prediction + workload classification logs (report §4.2, §4.5)
            self._create_index_if_missing("ml_predictions", [("username", 1), ("created_at", -1)])
            self._create_index_if_missing("ml_predictions", [("evaluation_status", 1), ("created_at", -1)])
            self._create_index_if_missing("ml_predictions", [("prediction_type", 1)])
            self._create_index_if_missing("ml_predictions", [("feedback_score", -1)])

            self._create_index_if_missing(
                "ml_workload_descriptions",
                [("username", 1), ("created_at", -1)]
            )
            self._create_index_if_missing(
                "ml_workload_descriptions",
                [("evaluation_status", 1), ("created_at", -1)]
            )
            self._create_index_if_missing("ml_workload_descriptions", [("final_cluster", 1)])
            self._create_index_if_missing("ml_workload_descriptions", [("feedback_score", -1)])
            self._create_index_if_missing("ml_retraining_runs", [("trained_at", -1)])
            self._create_index_if_missing("storage_lifecycle_reports", [("ran_at", -1)])

            # Phase 11: Terraform provisioning deployments
            self._create_index_if_missing("provision_deployments", [("user_id", 1), ("created_at", -1)])
            self._create_index_if_missing("provision_deployments", [("user_id", 1), ("status", 1)])
            self._create_index_if_missing("provision_deployments", [("deployment_name", 1)], unique=True)
        except Exception as e:
            logger.warning(f"Failed to ensure MongoDB indexes: {e}")

    def _create_index_if_missing(self, collection_name: str, keys, **kwargs) -> None:
        collection = self.db[collection_name]
        expected_keys = [(keys, 1)] if isinstance(keys, str) else list(keys)

        for index_info in collection.index_information().values():
            if index_info.get("key") != expected_keys:
                continue

            if kwargs.get("unique") and not index_info.get("unique"):
                logger.warning(
                    f"Index on {collection_name}.{expected_keys} exists without unique=True"
                )
            expected_ttl = kwargs.get("expireAfterSeconds")
            actual_ttl = index_info.get("expireAfterSeconds")
            if expected_ttl is not None and actual_ttl != expected_ttl:
                logger.warning(
                    f"Index on {collection_name}.{expected_keys} exists with expireAfterSeconds={actual_ttl}"
                )
            return

        collection.create_index(keys, **kwargs)

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
