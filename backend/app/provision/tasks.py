# =============================================================================
# MODULE: provision/tasks.py
# PURPOSE: Celery background tasks for provisioning — scheduled drift detection
# USED BY: celery_worker.py Beat schedule (daily 06:00 UTC)
# DEPENDS ON: drift_detector.py, byoc_credentials.py
# DO NOT:
#   - Run drift checks on destroyed deployments
#   - Use platform AWS credentials when owner BYOC is missing
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def scheduled_drift_check():
    """
    Celery Beat task: check all active deployments for drift.

    Uses each deployment owner's BYOC AWS credentials. Deployments without
    BYOC are skipped (no silent platform-credential fallback).
    """
    from app.database.mongo_client import get_database
    from app.provision.byoc_credentials import resolve_byoc_terraform_env
    from app.provision.drift_detector import detect_drift
    from app.provision.models import DeploymentStatus, DriftStatus

    DB = get_database()
    collection = DB["provision_deployments"]

    active_deployments = list(
        collection.find({"status": DeploymentStatus.DEPLOYED})
    )

    if not active_deployments:
        logger.info("Scheduled drift check: no active deployments found.")
        return {"checked": 0, "drift_found": 0, "skipped": 0}

    checked = 0
    drift_found = 0
    skipped = 0

    for deployment in active_deployments:
        deployment_name = deployment.get("deployment_name", "unknown")
        workspace = deployment.get("terraform_workspace", "")
        owner = deployment.get("user_id", "")
        config = deployment.get("config") or {}
        region = config.get("aws_region", "ap-south-1")

        if not workspace:
            logger.warning("Drift check skipped for %s: no workspace path", deployment_name)
            skipped += 1
            continue

        if not owner:
            logger.warning("Drift check skipped for %s: missing user_id", deployment_name)
            skipped += 1
            continue

        aws_creds = resolve_byoc_terraform_env(owner, region)
        if not aws_creds:
            logger.info(
                "Scheduled drift skipped for %s: BYOC AWS not configured for %s",
                deployment_name,
                owner,
            )
            from app.provision.models import DriftReport

            skip_report = DriftReport(
                status=DriftStatus.CHECK_FAILED,
                changes_detected=0,
                details=[
                    "Scheduled drift skipped: deployment owner has no active BYOC AWS credentials.",
                ],
                checked_at=datetime.utcnow(),
            )
            collection.update_one(
                {"deployment_name": deployment_name},
                {
                    "$push": {"drift_history": skip_report.model_dump()},
                    "$set": {
                        "latest_drift": DriftStatus.CHECK_FAILED,
                        "updated_at": datetime.utcnow(),
                    },
                },
            )
            skipped += 1
            continue

        try:
            drift_report = detect_drift(workspace, aws_credentials=aws_creds)

            collection.update_one(
                {"deployment_name": deployment_name},
                {
                    "$push": {"drift_history": drift_report.model_dump()},
                    "$set": {
                        "latest_drift": drift_report.status,
                        "updated_at": datetime.utcnow(),
                    },
                },
            )

            checked += 1
            if drift_report.status == DriftStatus.DRIFT_DETECTED:
                drift_found += 1
                logger.warning("Drift detected in deployment: %s", deployment_name)

        except Exception as e:
            logger.error("Drift check failed for %s: %s", deployment_name, e)

    logger.info(
        "Scheduled drift check complete: %s checked, %s with drift, %s skipped",
        checked,
        drift_found,
        skipped,
    )
    return {"checked": checked, "drift_found": drift_found, "skipped": skipped}
