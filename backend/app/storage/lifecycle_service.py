"""Lifecycle user actions, notifications, and pending demotion execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo.collection import Collection

from app.notifications import service as notification_service
from app.storage.lifecycle_policy import (
    SNOOZE_DAYS_DEFAULT,
    VALID_POLICIES,
    as_utc,
    normalize_lifecycle_policy,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

STORAGE_PAGE_LINK = "/dashboard/storage"


def _tier_label(tier: str) -> str:
    return {"hot": "Hot", "warm": "Warm", "cold": "Cold / Archive"}.get(tier, tier)


def notify_pending_demotion(
    username: str,
    filename: str,
    target_tier: str,
    monthly_savings: float,
    execute_after: datetime,
) -> str:
    savings_txt = f"${monthly_savings:.2f}/mo" if monthly_savings else "lower storage cost"
    execute_label = execute_after.strftime("%b %d, %Y")
    return notification_service.create_notification(
        username,
        title="Storage tier change scheduled",
        message=(
            f"'{filename}' hasn't been used recently. "
            f"Zenith will move it to {_tier_label(target_tier)} storage on {execute_label} "
            f"(est. {savings_txt}). Open Storage to Keep hot, Snooze, or Approve now."
        ),
        type="warning",
        link=STORAGE_PAGE_LINK,
        metadata={
            "category": "lifecycle_pending",
            "filename": filename,
            "target_tier": target_tier,
            "actions": ["keep_hot", "snooze", "approve"],
        },
    )


def notify_demotion_complete(
    username: str,
    filename: str,
    target_tier: str,
    provider_class: str,
) -> str:
    return notification_service.create_notification(
        username,
        title="Storage tier updated",
        message=(
            f"'{filename}' was moved to {_tier_label(target_tier)} ({provider_class}). "
            "Downloads may be slower; use Restore if the file is in archive storage."
        ),
        type="info",
        link=STORAGE_PAGE_LINK,
        metadata={"category": "lifecycle_completed", "filename": filename},
    )


def notify_manual_suggestion(
    username: str,
    filename: str,
    target_tier: str,
    monthly_savings: float,
) -> str:
    savings_txt = f"${monthly_savings:.2f}/mo" if monthly_savings else "some savings"
    return notification_service.create_notification(
        username,
        title="Storage savings suggestion",
        message=(
            f"'{filename}' could move to {_tier_label(target_tier)} storage "
            f"(est. {savings_txt}). Your policy is suggest-only — change policy on the file in Storage."
        ),
        type="info",
        link=STORAGE_PAGE_LINK,
        metadata={"category": "lifecycle_suggestion", "filename": filename},
    )


def find_user_file(files_db: Collection, username: str, filename: str) -> Optional[Dict[str, Any]]:
    return files_db.find_one({"owner_username": username, "filename": filename})


def execute_pending_demotion(
    file_record: Dict[str, Any],
    files_db: Collection,
    tier_change_functions: Dict[str, Any],
) -> bool:
    from app.storage.tiering_tasks import _perform_tier_change

    pending = file_record.get("lifecycle_pending_demotion") or {}
    target_tier = pending.get("target_tier")
    if not target_tier:
        return False
    priority = pending.get("priority")
    changed = _perform_tier_change(
        file_record,
        target_tier,
        tier_change_functions,
        files_db,
        priority=priority,
    )
    if changed:
        savings = float((priority or {}).get("factors", {}).get("estimated_monthly_savings", 0) or 0)
        if not savings and pending:
            savings = float(pending.get("estimated_monthly_savings", 0) or 0)
        files_db.update_one(
            {"_id": file_record["_id"]},
            {
                "$unset": {"lifecycle_pending_demotion": ""},
                "$set": {"lifecycle_last_demotion_at": datetime.now(timezone.utc)},
                "$inc": {"lifecycle_savings_total_usd": max(savings, 0)},
            },
        )
        owner = file_record.get("owner_username") or file_record.get("username")
        if owner:
            updated = files_db.find_one({"_id": file_record["_id"]}) or file_record
            notify_demotion_complete(
                owner,
                file_record.get("filename", ""),
                target_tier,
                updated.get("storage_class", target_tier),
            )
    return changed


def apply_lifecycle_action(
    files_db: Collection,
    username: str,
    filename: str,
    action: str,
    *,
    snooze_days: int = SNOOZE_DAYS_DEFAULT,
    tier_change_functions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    action = (action or "").lower().strip()
    if action not in ("keep_hot", "snooze", "approve"):
        raise ValueError(f"Invalid action: {action}")

    file_record = find_user_file(files_db, username, filename)
    if not file_record:
        raise LookupError(f"File not found: {filename}")

    now = datetime.now(timezone.utc)
    file_id = file_record["_id"]

    if action == "keep_hot":
        files_db.update_one(
            {"_id": file_id},
            {
                "$set": {
                    "lifecycle_policy": "keep_hot",
                    "lifecycle_snoozed_until": now + timedelta(days=snooze_days),
                    "lifecycle_updated_at": now,
                },
                "$unset": {"lifecycle_pending_demotion": ""},
            },
        )
        return {"status": "ok", "action": action, "filename": filename, "policy": "keep_hot"}

    if action == "snooze":
        pending = dict(file_record.get("lifecycle_pending_demotion") or {})
        execute_after = now + timedelta(days=snooze_days)
        pending["execute_after"] = execute_after
        files_db.update_one(
            {"_id": file_id},
            {
                "$set": {
                    "lifecycle_pending_demotion": pending,
                    "lifecycle_snoozed_until": execute_after,
                    "lifecycle_updated_at": now,
                },
            },
        )
        return {
            "status": "ok",
            "action": action,
            "filename": filename,
            "snoozed_until": execute_after.isoformat(),
        }

    if action == "approve":
        if not tier_change_functions:
            from app.storage.manager import (
                change_tier_on_aws,
                change_tier_on_azure,
                change_tier_on_gcp,
            )

            tier_change_functions = {
                "AWS": change_tier_on_aws,
                "GCP": change_tier_on_gcp,
                "Azure": change_tier_on_azure,
            }
        pending = file_record.get("lifecycle_pending_demotion")
        if not pending:
            raise ValueError("No pending tier change for this file")
        changed = execute_pending_demotion(file_record, files_db, tier_change_functions)
        if not changed:
            raise RuntimeError("Tier change failed")
        return {"status": "ok", "action": action, "filename": filename, "moved": True}

    raise ValueError(f"Unhandled action: {action}")
