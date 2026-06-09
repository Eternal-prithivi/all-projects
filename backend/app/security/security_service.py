"""Secure vault user actions and in-app notifications."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pymongo.collection import Collection

from app.notifications import service as notification_service
from app.security.security_policy import SNOOZE_DAYS_DEFAULT, get_user_security_preferences
from app.storage.secure_vault import (
    SecureVaultArchiveError,
    archive_secure_vault_object,
    delete_secure_vault_object,
    restore_secure_vault_object,
    resolve_secure_storage,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

SECURITY_PAGE_LINK = "/dashboard/security"


def notify_encryption_pending(username: str, filename: str, scan_reasons: Optional[list] = None) -> str:
    reason_hint = ""
    if scan_reasons:
        reason_hint = f" ({scan_reasons[0].replace('_', ' ')})"
    return notification_service.create_notification(
        username,
        title="Encryption required",
        message=(
            f"'{filename}' needs your encryption choice{reason_hint}. "
            "Open Security to choose cloud-managed or browser encryption."
        ),
        type="warning",
        link=SECURITY_PAGE_LINK,
        metadata={
            "category": "security_encryption_pending",
            "filename": filename,
            "actions": ["encrypt_now", "dismiss_encryption"],
        },
    )


def notify_stale_file_pending(
    username: str,
    filename: str,
    inactive_days: int,
    execute_after: datetime,
) -> str:
    execute_label = execute_after.strftime("%b %d, %Y")
    return notification_service.create_notification(
        username,
        title="Stale secure file",
        message=(
            f"'{filename}' has not been opened in {inactive_days} days. "
            f"Review by {execute_label} — archive, snooze, or delete from Security."
        ),
        type="warning",
        link=SECURITY_PAGE_LINK,
        metadata={
            "category": "security_stale_pending",
            "filename": filename,
            "inactive_days": inactive_days,
            "actions": ["archive", "snooze_stale", "approve_delete"],
        },
    )


def find_secure_file_doc(
    files_db: Collection, username: str, filename: str
) -> Optional[Dict[str, Any]]:
    return files_db.find_one({"owner_username": username, "filename": filename})


def apply_vault_action(
    files_db: Collection,
    username: str,
    filename: str,
    action: str,
    *,
    snooze_days: int = SNOOZE_DAYS_DEFAULT,
) -> Dict[str, Any]:
    file_doc = find_secure_file_doc(files_db, username, filename)
    if not file_doc:
        return {"ok": False, "detail": "File not found"}

    now = datetime.now(timezone.utc)

    if action == "encrypt_now":
        return {
            "ok": True,
            "action": action,
            "filename": filename,
            "open_encryption": True,
        }

    if action == "dismiss_encryption":
        return {"ok": True, "action": action, "filename": filename}

    if action == "snooze_stale":
        until = now + timedelta(days=snooze_days)
        files_db.update_one(
            {"_id": file_doc["_id"]},
            {
                "$set": {"stale_snoozed_until": until},
                "$unset": {"stale_pending_action": ""},
            },
        )
        return {"ok": True, "action": action, "snoozed_until": until.isoformat()}

    if action in ("archive", "restore"):
        file_csp = file_doc.get("csp") or "AWS"
        storage = resolve_secure_storage(username, file_csp)
        object_key = file_doc.get("s3_key") or storage.object_key(username, filename)
        try:
            if action == "archive":
                replica_name = archive_secure_vault_object(storage, object_key)
                files_db.update_one(
                    {"_id": file_doc["_id"]},
                    {
                        "$set": {
                            "vault_status": "archived",
                            "vault_storage_location": "replica",
                            "cloud_bucket": replica_name,
                            "archived_at": now,
                        },
                        "$unset": {"stale_pending_action": ""},
                    },
                )
                return {
                    "ok": True,
                    "action": action,
                    "vault_status": "archived",
                    "vault_storage_location": "replica",
                    "cloud_bucket": replica_name,
                }

            primary_name = restore_secure_vault_object(storage, object_key)
            files_db.update_one(
                {"_id": file_doc["_id"]},
                {
                    "$set": {
                        "vault_status": "active",
                        "vault_storage_location": "primary",
                        "cloud_bucket": primary_name,
                        "replication_enabled": False,
                    },
                    "$unset": {"archived_at": "", "stale_pending_action": ""},
                },
            )
            return {
                "ok": True,
                "action": action,
                "vault_status": "active",
                "vault_storage_location": "primary",
                "cloud_bucket": primary_name,
            }
        except SecureVaultArchiveError as exc:
            return {"ok": False, "detail": str(exc)}

    if action == "approve_delete":
        if (file_doc.get("vault_status") or "active") == "archived":
            return {
                "ok": False,
                "detail": "File is archived. Restore it before deleting.",
            }
        file_csp = file_doc.get("csp") or "AWS"
        storage = resolve_secure_storage(username, file_csp)
        object_key = file_doc.get("s3_key") or storage.object_key(username, filename)
        delete_secure_vault_object(storage, object_key)
        files_db.delete_one({"_id": file_doc["_id"]})
        return {"ok": True, "action": action, "deleted": True}

    return {"ok": False, "detail": f"Unknown action: {action}"}
