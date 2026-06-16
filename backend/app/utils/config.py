# =============================================================================
# MODULE: config.py  (79 lines)
# PURPOSE: Pydantic Settings — reads ALL env vars from backend/.env
#          Exposes a single 'settings' singleton used everywhere: from app.utils.config import settings
# ENV FILE: backend/.env (never commit — contains real credentials)
# USED BY: Every module that needs config — aws keys, mongo URI, secret key, etc.
# DO NOT:
#   - Instantiate Settings() more than once — use the shared 'settings' singleton
#   - Add defaults for security-sensitive fields (SECRET_KEY, AWS keys, etc.)
#   - Rename existing field names — every import uses the same attribute names
# =============================================================================
# backend/app/utils/config.py

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

# Local dev: backend/.env — Production (Render): OS env vars from the dashboard
env_path = Path(__file__).resolve().parents[2] / '.env'
_env_file = str(env_path) if env_path.is_file() else None


class Settings(BaseSettings):
    """
    Manages all application settings, including cloud provider credentials.
    """
    # env_file only when present locally; Render/Docker always use injected env vars
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- MongoDB Settings ---
    MONGO_CONNECTION_STRING: str
    MONGO_DB_NAME: str # Ensure this is also in your .env now

    # --- JWT Settings ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256" # Default value, can be overridden by .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Default value, can be overridden by .env

    # --- AWS Settings ---
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    PRIMARY_S3_REGION: str = 'ap-south-1' # Default value, can be overridden by .env
    REGULAR_S3_BUCKET_NAME: str # THIS IS THE FIELD THAT WAS MISSING AND NOW ADDED/CONFIRMED
    SECURE_S3_BUCKET_NAME: str
    REPLICA_S3_BUCKET_NAME: str
    REPLICA_S3_REGION: str
    CELERY_BROKER_URL: str # Moved here for grouping, was mixed before

    # --- GCP Credentials ---
    GCP_SERVICE_ACCOUNT_JSON_PATH: str = ""  # Leave empty if no GCP key file (DEMO_MODE bypasses real calls)
    GCP_BUCKET_NAME: str
    GCP_SECURE_BUCKET_NAME: str  # Dedicated GCS vault (separate from GCP_BUCKET_NAME)
    GCP_SECURE_REPLICA_BUCKET_NAME: str = ""  # Fixed replica GCS bucket for secure vault
    GCP_REPLICA_BUCKET_NAME: str = ""  # Deprecated alias — use GCP_SECURE_REPLICA_BUCKET_NAME
    GCP_PROJECT_ID: str
    GCP_ZONE: str = "us-central1-a" # Free tier zone + a specific sub-zone

    # GCP Billing (BigQuery export — Cost Analysis)
    GCP_BILLING_DATASET_ID: str = ""
    GCP_BILLING_TABLE_ID: str = ""

    # VM Cluster Configuration
    CLUSTER_MAX_VMS_DEFAULT: int = 4
    PERFORMANCE_CLUSTER_MAX_VMS: int = 4  # legacy alias
    STORAGE_CLUSTER_MAX_VMS: int = 4  # legacy alias
    VM_EXTENDED_CLUSTERS_ENABLED: bool = True

    # Default machine types for the clusters (adjust as needed for demo/credits)
    PERFORMANCE_VM_MACHINE_TYPE: str = "e2-micro"
    STORAGE_VM_MACHINE_TYPE: str = "e2-micro"
    STORAGE_VM_DISK_SIZE_GB: int = 20 # Example: 20GB disk for storage VMs # Ensure this is in your .env now
    
    # VM Metrics Configuration
    USE_REAL_METRICS: bool = False  # Set to True for real GCP metrics, False for simulated

    # VM adaptive agent (enterprise Step 4) — off by default for safe rollout
    VM_AUTO_MIGRATE_ENABLED: bool = False
    VM_AUTO_MIGRATE_MIN_SCORE: int = 85

    # Terminate VMs (and disks) when the last user releases — no idle disk charges
    VM_DELETE_ON_IDLE: bool = True

    # --- Demo Mode Configuration ---
    DEMO_MODE: bool = False  # Set to True to use mock data instead of real API calls (zero cost!)
    
    # --- Real-Time Mode Configuration ---
    REAL_TIME_MODE: bool = False  # Set to True to disable all caching and fetch live data (higher costs!)
    
    # --- Razorpay Payment Configuration ---
    RAZORPAY_KEY_ID: str = ""  # Razorpay Key ID (rzp_test_xxx for test mode)
    RAZORPAY_KEY_SECRET: str = ""  # Razorpay Key Secret
    RAZORPAY_WEBHOOK_SECRET: str = ""  # Webhook secret for signature verification
    
    # --- Production Configuration ---
    FRONTEND_URL: str = "http://localhost:5173"  # Update to your production domain
    BACKEND_URL: str = "http://localhost:8000"   # Production: https://api.rajverse.me
    PUBLIC_API_URL: str = ""  # Defaults to BACKEND_URL when empty
    ENVIRONMENT: str = "development"  # development, staging, production

    # Platform cloud liability caps (USD, estimated)
    PLATFORM_MONTHLY_BUDGET_USD: float = 0.0  # 0 = use platform_settings doc only
    SUBSCRIPTION_GRACE_DAYS: int = 3
    MAX_UPLOAD_BYTES_FREE: int = 25 * 1024 * 1024  # 25 MB
    MAX_UPLOAD_BYTES_PAID: int = 100 * 1024 * 1024  # 100 MB
    FREE_TIER_VM_IDLE_MINUTES: int = 15
    PAID_TIER_VM_IDLE_MINUTES: int = 30

    # New-user signup alerts (defaults to aangatla957@gmail.com if unset)
    SIGNUP_NOTIFY_EMAIL: str = "aangatla957@gmail.com"

    # Signup trust — unset uses platform_settings / production default
    REQUIRE_EMAIL_VERIFICATION: Optional[bool] = None

    # --- Single-tenant / owner account (optional) ---
    # Comma-separated Zenith usernames that always receive PLATFORM_OWNER_PLAN on this deployment.
    # Example: PLATFORM_OWNER_USERNAMES=Tanjore developer
    PLATFORM_OWNER_USERNAMES: str = ""
    PLATFORM_OWNER_PLAN: str = "enterprise"

    # --- Azure Credentials ---
    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_STORAGE_ACCOUNT_KEY: str
    AZURE_CONTAINER_NAME: str
    AZURE_SECURE_CONTAINER_NAME: str  # Dedicated secure vault container (separate from storage)
    AZURE_SECURE_REPLICA_CONTAINER_NAME: str = ""  # Fixed replica container for secure vault
    AZURE_SECURE_STORAGE_ACCOUNT_NAME: str = ""  # Optional; defaults to AZURE_STORAGE_ACCOUNT_NAME
    AZURE_SECURE_STORAGE_ACCOUNT_KEY: str = ""  # Optional; defaults to AZURE_STORAGE_ACCOUNT_KEY
    AZURE_SUBSCRIPTION_ID: str = ""
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_RESOURCE_GROUP: str = "zenith-rg"
    AZURE_LOCATION: str = "eastus"

    # --- Platform multi-region storage catalog (optional) ---
    # JSON file path (relative to backend/) or absolute path to region→bucket map.
    PLATFORM_STORAGE_CATALOG_JSON: str = ""
    # Inline JSON array alternative to file (overrides file when non-empty).
    PLATFORM_STORAGE_CATALOG: str = ""
    # Default region slug when catalog has multiple regions (e.g. asia).
    PLATFORM_STORAGE_DEFAULT_SLUG: str = "asia"

settings = Settings()