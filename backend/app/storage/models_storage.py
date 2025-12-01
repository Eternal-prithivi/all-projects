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
    
    # --- Fields for security feature (now correctly re-integrated) ---
    is_sensitive: bool = False
    is_encrypted: Optional[bool] = False
    encryption_method: Optional[str] = "none"  # "none" | "server-side" | "client-side"
    encryption_status: Optional[str] = "none"  # "none" | "pending" | "awaiting_choice" | "encrypted" | "failed"
    awaiting_encryption_choice: bool = False
    client_side_encrypted: bool = False  # True if encrypted with user's password

