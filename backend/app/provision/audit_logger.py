# =============================================================================
# MODULE: provision/audit_logger.py
# PURPOSE: Append-only audit logging for all Terraform provisioning actions
# SOURCE: Adapted from aws-provision-using-terraform/team-management/audit.py
# STORES: provision_audit_log collection in MongoDB
# USED BY: routes_provision.py (every plan, apply, destroy, remediate, drift action)
# DO NOT:
#   - Delete or modify existing audit records — append-only design
#   - Skip audit logging for any state-changing operation
# =============================================================================
"""
Provision Audit Logger.

Every infrastructure action (plan, apply, destroy, remediate, drift check)
is recorded with the actor, timestamp, deployment, status, and details.
The log is append-only and queryable by actor, deployment, action, or date.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from app.database.mongo_client import get_database

logger = logging.getLogger(__name__)

AUDIT_RETENTION_DAYS = 90


def _get_audit_collection():
    """Get the provision_audit_log MongoDB collection."""
    DB = get_database()
    return DB["provision_audit_log"]


def log_provision_action(
    *,
    action: str,
    actor: str,
    deployment_id: str,
    status: str,
    details: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """
    Log a provision action to the audit trail.

    Args:
        action: Action type — "plan", "apply", "destroy", "remediate",
                "drift_check", "role_assign", etc.
        actor: Username of the user who performed the action.
        deployment_id: ID of the deployment affected (or "system" for admin ops).
        status: Outcome — "success", "failed", "denied", "pending".
        details: Optional dict with extra context (config, output excerpt, etc.).
        error: Optional error message if the action failed.

    Returns:
        The created audit event dict (without _id).
    """
    event = {
        "action": action,
        "actor": actor,
        "deployment_id": deployment_id,
        "status": status,
        "details": details or {},
        "error": error,
        "timestamp": datetime.utcnow(),
    }

    try:
        collection = _get_audit_collection()
        collection.insert_one(event.copy())  # copy so _id doesn't leak into return
        logger.info(f"Audit: {action} by {actor} on {deployment_id} → {status}")
    except Exception as e:
        # Audit logging must never crash the main operation
        logger.error(f"Failed to write audit log: {e}")

    return event


def get_deployment_audit_log(deployment_id: str) -> list[dict[str, Any]]:
    """Get all audit events for a specific deployment, newest first."""
    collection = _get_audit_collection()
    events = list(
        collection.find(
            {"deployment_id": deployment_id},
            {"_id": 0},
        ).sort("timestamp", -1)
    )
    return events


def _build_user_audit_query(
    username: str,
    *,
    action: Optional[str] = None,
    days: int = AUDIT_RETENTION_DAYS,
) -> dict[str, Any]:
    days = max(7, min(days, 90))
    cutoff = datetime.utcnow() - timedelta(days=days)
    query: dict[str, Any] = {
        "actor": username,
        "timestamp": {"$gte": cutoff},
    }
    if action and action != "all":
        if action == "policy":
            query["action"] = {"$regex": r"^policy_"}
        else:
            query["action"] = action
    return query


def ensure_audit_indexes() -> None:
    """Compound query index + TTL retention on provision_audit_log."""
    collection = _get_audit_collection()
    try:
        collection.create_index([("actor", 1), ("timestamp", -1)], background=True)
        collection.create_index(
            "timestamp",
            expireAfterSeconds=AUDIT_RETENTION_DAYS * 86400,
            background=True,
        )
    except Exception as e:
        logger.warning(f"provision_audit_log index setup: {e}")


def get_user_audit_log(
    username: str,
    *,
    limit: int = 10,
    skip: int = 0,
    action: Optional[str] = None,
    days: int = AUDIT_RETENTION_DAYS,
) -> tuple[list[dict[str, Any]], int]:
    """Audit events for a user, newest first. Returns (page, total_matching)."""
    collection = _get_audit_collection()
    query = _build_user_audit_query(username, action=action, days=days)

    total = collection.count_documents(query)
    events = list(
        collection.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(max(0, skip))
        .limit(max(1, min(limit, 25)))
    )
    return events, total


def export_user_audit_csv_rows(
    username: str,
    *,
    action: Optional[str] = None,
    days: int = AUDIT_RETENTION_DAYS,
    max_rows: int = 5000,
) -> list[dict[str, Any]]:
    """All matching audit rows for CSV export (capped)."""
    collection = _get_audit_collection()
    query = _build_user_audit_query(username, action=action, days=days)
    return list(
        collection.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .limit(max_rows)
    )


def get_recent_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """Get the most recent audit events across all users."""
    collection = _get_audit_collection()
    events = list(
        collection.find(
            {},
            {"_id": 0},
        ).sort("timestamp", -1).limit(limit)
    )
    return events


def generate_audit_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Generate an audit summary report for a date range.

    Returns counts grouped by action, actor, and status.
    """
    collection = _get_audit_collection()
    query: dict[str, Any] = {}
    if start_date or end_date:
        query["timestamp"] = {}
        if start_date:
            query["timestamp"]["$gte"] = start_date
        if end_date:
            query["timestamp"]["$lte"] = end_date

    events = list(collection.find(query, {"_id": 0}))

    report: dict[str, Any] = {
        "total_events": len(events),
        "by_action": {},
        "by_actor": {},
        "by_status": {},
    }

    for event in events:
        action = event.get("action", "unknown")
        report["by_action"][action] = report["by_action"].get(action, 0) + 1

        actor = event.get("actor", "unknown")
        report["by_actor"][actor] = report["by_actor"].get(actor, 0) + 1

        status = event.get("status", "unknown")
        report["by_status"][status] = report["by_status"].get(status, 0) + 1

    return report
