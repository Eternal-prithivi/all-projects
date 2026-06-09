"""Nightly stale secure-file awareness job."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from celery import shared_task

from app.database.mongo_client import get_database
from app.security.security_intelligence import inactive_days
from app.security.security_policy import get_user_security_preferences
from app.security.security_service import notify_stale_file_pending
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def _is_snoozed(file_doc: Dict[str, Any], now: datetime) -> bool:
    until = file_doc.get("stale_snoozed_until")
    if until is None:
        return False
    if isinstance(until, datetime):
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > now
    return False


@shared_task(name="run_security_stale_check")
def run_security_stale_check() -> Dict[str, Any]:
    """Notify users about secure files inactive beyond their stale_file_days threshold."""
    db = get_database()
    secure_files = db["secure_files"]
    now = datetime.now(timezone.utc)

    owners: List[str] = secure_files.distinct("owner_username")
    notified = 0
    skipped_notice_zero = 0

    for username in owners:
        if not username:
            continue
        prefs = get_user_security_preferences(username)
        threshold = int(prefs.get("stale_file_days", 90))
        notice_days = int(prefs.get("stale_notice_days", 7))

        cursor = secure_files.find(
            {
                "owner_username": username,
                "awaiting_encryption_choice": {"$ne": True},
                "$or": [{"vault_status": "active"}, {"vault_status": {"$exists": False}}],
            }
        )
        for file_doc in cursor:
            inactive = inactive_days(file_doc, now)
            if inactive is None or inactive < threshold:
                continue
            if _is_snoozed(file_doc, now):
                continue
            if file_doc.get("stale_pending_action"):
                continue

            execute_after = now + timedelta(days=notice_days)
            if notice_days == 0:
                skipped_notice_zero += 1
                secure_files.update_one(
                    {"_id": file_doc["_id"]},
                    {
                        "$set": {
                            "stale_pending_action": {
                                "notified_at": now,
                                "execute_after": execute_after,
                                "suggested_action": "review",
                            }
                        }
                    },
                )
                continue

            notify_stale_file_pending(
                username,
                file_doc.get("filename", ""),
                inactive,
                execute_after,
            )
            secure_files.update_one(
                {"_id": file_doc["_id"]},
                {
                    "$set": {
                        "stale_pending_action": {
                            "notified_at": now,
                            "execute_after": execute_after,
                            "suggested_action": "review",
                        }
                    }
                },
            )
            notified += 1

    logger.info(
        "Security stale check complete: notified=%s notice_zero_only=%s",
        notified,
        skipped_notice_zero,
    )
    return {
        "success": True,
        "notified": notified,
        "notice_zero_marked": skipped_notice_zero,
    }
