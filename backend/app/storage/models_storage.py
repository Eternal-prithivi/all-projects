from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class FileMetadata(BaseModel):
    """
    Pydantic model for storing file metadata in MongoDB.
    This is the complete, unified model for all application features.
    """
    filename: str
    s3_key: str # This field now represents the 'object_key' on any CSP
    owner_username: str
    size_bytes: int
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    
    # --- Fields for multi-cloud and tiering (from our new model) ---
    csp: str = "AWS"
    storage_class: str = "Standard"
    
    # --- Fields for long-term optimization model (from our new model) ---
    last_accessed_at: Optional[datetime] = None
    access_frequency_score: int = 0
    access_history: Optional[list] = None  # last N download timestamps for velocity signals

    # Upload context for smarter lifecycle (from analyze step)
    upload_user_priority: Optional[str] = None
    upload_user_intent: Optional[str] = None
    initial_planned_tier: Optional[str] = None  # ML ensemble tier at upload time
    
    # --- Fields for security feature (now correctly re-integrated) ---
    is_sensitive: bool = False
    is_encrypted: Optional[bool] = False
    encryption_method: Optional[str] = "none"  # "none" | "server-side" | "client-side"
    encryption_status: Optional[str] = "none"  # "none" | "pending" | "awaiting_choice" | "encrypted" | "failed"
    awaiting_encryption_choice: bool = False
    client_side_encrypted: bool = False  # True if encrypted with user's password

    # Multi-bucket BYOC / platform: which bucket or container holds this object
    cloud_bucket: Optional[str] = None
    region: Optional[str] = None
    # Platform multi-region: catalog slug (asia, us, europe, africa) and Azure account name
    platform_slug: Optional[str] = None
    cloud_account: Optional[str] = None

    # Lifecycle policy (auto | keep_hot | aggressive | manual)
    lifecycle_policy: str = "auto"
    lifecycle_pending_demotion: Optional[dict] = None
    lifecycle_snoozed_until: Optional[datetime] = None
    lifecycle_last_suggestion_at: Optional[datetime] = None
    lifecycle_savings_total_usd: float = 0.0

