# =============================================================================
# MODULE: mongo_client.py
# PURPOSE: Singleton MongoDB connection — every route uses this to get collections
# DATABASE: name from settings.MONGO_DB_NAME (see backend/.env)
# NOTE: Connection is lazy so Uvicorn can bind and pass Render's HTTP health
#       check before Atlas/index setup finishes (avoids 5s timeout on cold start).
# =============================================================================
from __future__ import annotations

import threading

from pymongo import MongoClient

from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_MONGO_TIMEOUT_MS = 8000


class MongoDB:
    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.db = None
        self._lock = threading.Lock()
        self._indexes_ensured = False

    def connect(self) -> bool:
        """Connect to Atlas and ensure indexes (idempotent). Returns True on success."""
        if self.db is not None:
            return True

        with self._lock:
            if self.db is not None:
                return True
            try:
                self.client = MongoClient(
                    settings.MONGO_CONNECTION_STRING,
                    serverSelectionTimeoutMS=_MONGO_TIMEOUT_MS,
                    connectTimeoutMS=_MONGO_TIMEOUT_MS,
                )
                self.client.admin.command("ping")
                self.db = self.client[settings.MONGO_DB_NAME]
                print("✅ Successfully connected to MongoDB.")
                if not self._indexes_ensured:
                    self._indexes_ensured = True
                    threading.Thread(target=self.ensure_indexes, daemon=True).start()
                return True
            except Exception as e:
                print(f"❌ Error connecting to MongoDB: {e}")
                self.client = None
                self.db = None
                return False

    def is_connected(self) -> bool:
        return self.db is not None

    def ensure_indexes(self) -> None:
        """
        Create essential indexes used across the app.

        This is a lightweight, idempotent operation that makes queries faster and
        prevents accidental duplicates (where appropriate).
        """
        if self.db is None:
            return

        try:
            self._ensure_files_unique_index()
            self._create_index_if_missing("files", [("owner_username", 1), ("last_accessed_at", -1)])
            self._create_index_if_missing("files", [("storage_class", 1), ("last_accessed_at", -1)])
            self._create_index_if_missing("files", [("last_tier_change", -1)])

            self._create_index_if_missing("secure_files", [("owner_username", 1), ("filename", 1)])
            self._create_index_if_missing(
                "secure_files",
                [("owner_username", 1), ("is_sensitive", 1), ("is_encrypted", 1)],
            )
            self._create_index_if_missing(
                "secure_files", [("owner_username", 1), ("last_accessed_at", -1)]
            )

            self._create_index_if_missing("sessions", [("username", 1), ("last_active", -1)])
            self._create_index_if_missing("activity_log", [("username", 1), ("timestamp", -1)])
            self._ensure_users_unique_index()
            self._ensure_users_email_unique_index()
            self._create_index_if_missing(
                "byoc_credentials",
                [("username", 1), ("csp", 1), ("is_active", 1)],
            )
            self._create_index_if_missing("vm_metrics", [("vm_name", 1), ("timestamp", -1)])
            self._create_index_if_missing("vm_assignments", [("status", 1)])
            self._create_index_if_missing(
                "vm_assignments", [("user_id", 1), ("assigned_at", -1)]
            )
            self._create_index_if_missing(
                "files", [("owner_username", 1), ("upload_date", -1)]
            )
            self._create_index_if_missing(
                "secure_files", [("owner_username", 1), ("upload_date", -1)]
            )
            self._create_index_if_missing("password_reset_requests", [("token_hash", 1)])
            self._create_index_if_missing(
                "password_reset_requests",
                "expires_at",
                expireAfterSeconds=0,
            )

            self._create_index_if_missing("ml_predictions", [("username", 1), ("created_at", -1)])
            self._create_index_if_missing("ml_predictions", [("evaluation_status", 1), ("created_at", -1)])
            self._create_index_if_missing("ml_predictions", [("prediction_type", 1)])
            self._create_index_if_missing("ml_predictions", [("feedback_score", -1)])

            self._create_index_if_missing(
                "ml_workload_descriptions",
                [("username", 1), ("created_at", -1)],
            )
            self._create_index_if_missing(
                "ml_workload_descriptions",
                [("evaluation_status", 1), ("created_at", -1)],
            )
            self._create_index_if_missing("ml_workload_descriptions", [("final_cluster", 1)])
            self._create_index_if_missing("ml_workload_descriptions", [("feedback_score", -1)])
            self._create_index_if_missing("ml_retraining_runs", [("trained_at", -1)])
            self._create_index_if_missing("storage_lifecycle_reports", [("ran_at", -1)])

            self._create_index_if_missing("provision_deployments", [("user_id", 1), ("created_at", -1)])
            self._create_index_if_missing("provision_deployments", [("user_id", 1), ("status", 1)])
            self._create_index_if_missing("provision_deployments", [("deployment_name", 1)], unique=True)

            self._create_index_if_missing("organization_members", [("username", 1)], unique=True)
            self._create_index_if_missing("organization_members", [("org_id", 1)])
            self._create_index_if_missing("organization_invites", [("token", 1)], unique=True)
            self._create_index_if_missing("organization_invites", [("org_id", 1), ("email", 1)])
            self._create_index_if_missing(
                "dashboard_cost_snapshots", [("username", 1), ("date", 1)]
            )
            self._create_index_if_missing(
                "organization_approval_requests", [("org_id", 1), ("status", 1)]
            )
            self._create_index_if_missing(
                "organization_action_items", [("org_id", 1), ("status", 1)]
            )
            self._create_index_if_missing("organization_subscriptions", [("org_id", 1)], unique=True)

            self._create_index_if_missing("vm_assignments", [("org_id", 1)])
            self._create_index_if_missing("vm_assignments", [("org_id", 1), ("created_by", 1)])
            self._create_index_if_missing("provision_deployments", [("org_id", 1)])
            self._create_index_if_missing("provision_deployments", [("org_id", 1), ("created_by", 1)])
            self._create_index_if_missing("files", [("org_id", 1)])
            self._create_index_if_missing("files", [("org_id", 1), ("created_by", 1)])
            self._create_index_if_missing("payment_orders", [("org_id", 1)])
        except Exception as e:
            logger.warning("Failed to ensure MongoDB indexes: %s", e)

    def _ensure_files_unique_index(self) -> None:
        """
        Allow the same filename in different regions/buckets (multi-region platform storage).
        Replaces legacy unique index on (owner_username, filename) only.
        """
        collection = self.db["files"]
        legacy_keys = [("owner_username", 1), ("filename", 1)]
        new_keys = [
            ("owner_username", 1),
            ("filename", 1),
            ("csp", 1),
            ("cloud_bucket", 1),
            ("region", 1),
        ]

        indexes = collection.index_information()
        has_new = any(
            info.get("key") == new_keys and info.get("unique")
            for info in indexes.values()
        )
        if has_new:
            return

        for name, info in indexes.items():
            if info.get("key") == legacy_keys and info.get("unique"):
                logger.info("Dropping legacy files unique index %s", name)
                collection.drop_index(name)
                break

        logger.info("Creating multi-region files unique index on %s", new_keys)
        collection.create_index(new_keys, unique=True, name="files_owner_filename_csp_bucket_region")

    def _ensure_users_unique_index(self) -> None:
        """Replace legacy non-unique users.username index with a unique index."""
        if self.db is None:
            return
        collection = self.db["users"]
        keys = [("username", 1)]
        for name, info in list(collection.index_information().items()):
            if info.get("key") != keys:
                continue
            if info.get("unique"):
                return
            dupes = list(
                collection.aggregate(
                    [
                        {"$group": {"_id": "$username", "count": {"$sum": 1}}},
                        {"$match": {"count": {"$gt": 1}}},
                        {"$limit": 1},
                    ]
                )
            )
            if dupes:
                logger.warning(
                    "users.username index is not unique and duplicate usernames exist; "
                    "resolve duplicates before upgrading the index"
                )
                return
            logger.info("Replacing non-unique users.username index %s with unique index", name)
            collection.drop_index(name)
            break
        collection.create_index(keys, unique=True)

    def _ensure_users_email_unique_index(self) -> None:
        """
        Ensure a sparse unique index on users.email.

        sparse=True means documents with no 'email' field (e.g. SSO-only
        accounts) are excluded from the uniqueness constraint, so they never
        block each other.

        Before creating/upgrading the index we check for existing duplicates so
        we never crash on a DB that already has dirty data — matching the same
        safety pattern used for users.username above.
        """
        if self.db is None:
            return
        collection = self.db["users"]
        keys = [("email", 1)]

        for name, info in list(collection.index_information().items()):
            if info.get("key") != keys:
                continue
            if info.get("unique") and info.get("sparse"):
                # Index already correct — nothing to do.
                return
            # Index exists but is missing unique/sparse — check for duplicates
            # before dropping and recreating it.
            dupes = list(
                collection.aggregate(
                    [
                        {"$match": {"email": {"$exists": True, "$ne": None}}},
                        {"$group": {"_id": "$email", "count": {"$sum": 1}}},
                        {"$match": {"count": {"$gt": 1}}},
                        {"$limit": 1},
                    ]
                )
            )
            if dupes:
                logger.warning(
                    "users.email index cannot be made unique: duplicate emails exist. "
                    "Resolve duplicates in the database before re-deploying."
                )
                return
            logger.info("Replacing non-unique users.email index %s with sparse unique index", name)
            collection.drop_index(name)
            break

        collection.create_index(keys, unique=True, sparse=True, name="users_email_unique")
        logger.info("✅ users.email unique sparse index ensured.")

    def _create_index_if_missing(self, collection_name: str, keys, **kwargs) -> None:
        collection = self.db[collection_name]
        expected_keys = [(keys, 1)] if isinstance(keys, str) else list(keys)

        for index_info in collection.index_information().values():
            if index_info.get("key") != expected_keys:
                continue

            if kwargs.get("unique") and not index_info.get("unique"):
                logger.warning(
                    "Index on %s.%s exists without unique=True",
                    collection_name,
                    expected_keys,
                )
            expected_ttl = kwargs.get("expireAfterSeconds")
            actual_ttl = index_info.get("expireAfterSeconds")
            if expected_ttl is not None and actual_ttl != expected_ttl:
                logger.warning(
                    "Index on %s.%s exists with expireAfterSeconds=%s",
                    collection_name,
                    expected_keys,
                    actual_ttl,
                )
            return

        collection.create_index(keys, **kwargs)

    def get_collection(self, collection_name: str):
        if not self.connect():
            return None
        return self.db[collection_name]


mongodb_client = MongoDB()


def get_database():
    """Get database instance for VM management and other operations."""
    if not mongodb_client.connect():
        raise RuntimeError("Database not initialized. MongoDB connection failed.")
    return mongodb_client.db


def get_users_collection():
    return mongodb_client.get_collection("users")
