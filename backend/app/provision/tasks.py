# =============================================================================
# MODULE: provision/tasks.py
# PURPOSE: Celery background tasks for provisioning — scheduled drift detection
# USED BY: celery_worker.py Beat schedule (daily 06:00 UTC)
# DEPENDS ON: drift_detector.py, terraform_runner.py
# DO NOT:
#   - Run drift checks on destroyed deployments
#   - Remove the drift history updates — they're audit-critical
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def scheduled_drift_check():
    """
    Celery Beat task: check all active deployments for drift.

    Runs daily at 06:00 UTC (matching the original Terraform project's
    GitHub Actions cron schedule).
    """
    from app.database.mongo_client import get_database
    from app.provision.drift_detector import detect_drift
    from app.provision.models import DeploymentStatus

    DB = get_database()
    collection = DB["provision_deployments"]

    # Find all deployed (active) deployments
    active_deployments = list(
        collection.find({"status": DeploymentStatus.DEPLOYED})
    )

    if not active_deployments:
        logger.info("Scheduled drift check: no active deployments found.")
        return {"checked": 0, "drift_found": 0}

    checked = 0
    drift_found = 0

    for deployment in active_deployments:
        deployment_name = deployment.get("deployment_name", "unknown")
        workspace = deployment.get("terraform_workspace", "")

        if not workspace:
            logger.warning(f"Drift check skipped for {deployment_name}: no workspace path")
            continue

        try:
            # Note: scheduled drift checks run without BYOC credentials
            # (would need a credential store for background jobs — for now,
            # uses the server's own AWS credentials if configured)
            drift_report = detect_drift(workspace)

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
            if drift_report.status == "drift_detected":
                drift_found += 1
                logger.warning(f"Drift detected in deployment: {deployment_name}")

        except Exception as e:
            logger.error(f"Drift check failed for {deployment_name}: {e}")

    logger.info(f"Scheduled drift check complete: {checked} checked, {drift_found} with drift")
    return {"checked": checked, "drift_found": drift_found}
