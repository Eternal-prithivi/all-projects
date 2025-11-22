# backend/app/utils/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

# This builds the correct path to the .env file in the project's root
# Assuming .env is two levels up from this file (e.g., backend/app/utils/config.py -> backend/.env)
env_path = Path(__file__).resolve().parents[2] / '.env'

class Settings(BaseSettings):
    """
    Manages all application settings, including cloud provider credentials.
    """
    # Using model_config for Pydantic v2 setup for loading .env
    model_config = SettingsConfigDict(env_file=env_path, extra="ignore")

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
    GCP_SERVICE_ACCOUNT_JSON_PATH: str
    GCP_BUCKET_NAME: str
    GCP_PROJECT_ID: str
    GCP_ZONE: str = "us-central1-a" # Free tier zone + a specific sub-zone

    # VM Cluster Configuration (for your demo)
    PERFORMANCE_CLUSTER_MAX_VMS: int = 2
    STORAGE_CLUSTER_MAX_VMS: int = 2

    # Default machine types for the clusters (adjust as needed for demo/credits)
    PERFORMANCE_VM_MACHINE_TYPE: str = "e2-micro"
    STORAGE_VM_MACHINE_TYPE: str = "e2-micro"
    STORAGE_VM_DISK_SIZE_GB: int = 20 # Example: 20GB disk for storage VMs # Ensure this is in your .env now
    
    # VM Metrics Configuration
    USE_REAL_METRICS: bool = False  # Set to True for real GCP metrics, False for simulated

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
    BACKEND_URL: str = "http://localhost:8000"   # Update to your production API domain
    ENVIRONMENT: str = "development"  # development, staging, production

    # --- Azure Credentials ---
    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_STORAGE_ACCOUNT_KEY: str
    AZURE_CONTAINER_NAME: str
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str

settings = Settings()