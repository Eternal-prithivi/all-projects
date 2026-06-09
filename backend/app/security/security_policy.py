"""Secure vault user preferences and upload default resolution."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from app.database.mongo_client import get_database

SecurityEncryptionDefault = Literal["ask", "server-side", "client-side"]
SecurityCspDefault = Literal["AWS", "GCP", "Azure"]

DEFAULT_SECURITY_PREFS: Dict[str, Any] = {
    "default_security_encryption": "ask",
    "always_ask_encryption": False,
    "default_security_csp": "AWS",
    "default_security_replication": False,
    "stale_file_days": 90,
    "stale_notice_days": 7,
    "ml_assisted_scan": True,
}

SNOOZE_DAYS_DEFAULT = 30


def get_user_security_preferences(username: str) -> Dict[str, Any]:
    db = get_database()
    user = db["users"].find_one({"username": username}, {"settings.preferences": 1})
    prefs = (user or {}).get("settings", {}).get("preferences", {}) or {}
    merged = {**DEFAULT_SECURITY_PREFS}
    for key in DEFAULT_SECURITY_PREFS:
        if key in prefs and prefs[key] is not None:
            merged[key] = prefs[key]
    return merged


def resolve_upload_encryption_defaults(
    username: str,
    *,
    encrypt_manual: bool = False,
    always_ask_encryption: bool = False,
    explicit_encryption: Optional[str] = None,
) -> Dict[str, Any]:
    """Determine whether upload must enter encryption wizard."""
    prefs = get_user_security_preferences(username)
    ask_always = always_ask_encryption or bool(prefs.get("always_ask_encryption"))
    default_enc = explicit_encryption or prefs.get("default_security_encryption", "ask")

    if encrypt_manual or ask_always:
        return {
            "needs_encryption_choice": True,
            "default_encryption_method": None,
            "always_ask": ask_always,
        }
    return {
        "needs_encryption_choice": default_enc == "ask",
        "default_encryption_method": None if default_enc == "ask" else default_enc,
        "always_ask": ask_always,
    }
