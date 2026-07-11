"""Helpers for Zenith user API keys (sk-prod-*)."""
from datetime import datetime
from typing import Optional, Tuple

from app.database.mongo_client import get_database


def touch_api_key_last_used(api_key: str) -> None:
    """Record last-used timestamp for a valid, non-revoked API key."""
    if not api_key or not api_key.startswith("sk-prod-"):
        return
    db = get_database()
    db["api_keys"].update_one(
        {"key": api_key, "revoked": {"$ne": True}},
        {"$set": {"last_used": datetime.utcnow()}},
    )


def resolve_user_from_api_key(api_key: str) -> Optional[Tuple[str, str]]:
    """
    Look up username and key_id for a platform API key.
    Returns (username, key_id) or None.
    """
    if not api_key or not api_key.startswith("sk-prod-"):
        return None
    db = get_database()
    doc = db["api_keys"].find_one({"key": api_key, "revoked": {"$ne": True}})
    if not doc:
        return None
    touch_api_key_last_used(api_key)
    return doc.get("username"), doc.get("key_id")
