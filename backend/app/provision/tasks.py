# =============================================================================
# MODULE: provision/tasks.py
# PURPOSE: Celery background tasks for provisioning — scheduled drift detection
# USED BY: celery_worker.py Beat schedule (daily 06:00 UTC)
# DEPENDS ON: drift_detector.py, boto3_drift.py, engine_resolver.py, byoc_credentials.py
# DO NOT:
#   - Run drift checks on destroyed deployments
#   - Use platform AWS credentials when owner BYOC is missing
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_TERRAFORM_PLACEHOLDER_WORKSPACES = frozenset({"fast-path", "boto3", ""})


def _run_scheduled_drift(
    deployment: dict[str, Any],
    aws_creds: dict[str, str],
):
    """Run drift check using the engine recorded at plan time (Terraform or Boto3)."""
    from app.provision.boto3_drift import detect_drift_boto3
    from app.provision.drift_detector import detect_drift
    from app.provision.engine_resolver import deployment_engine

    config = deployment.get("config") or {}
    engine = deployment_engine(deployment)

    if engine == "boto3":
        return detect_drift_boto3(
            config,
            aws_creds,
            deployment.get("boto3_context"),
        )

    workspace = deployment.get("terraform_workspace", "")
    if not workspace or workspace in _TERRAFORM_PLACEHOLDER_WORKSPACES:
        from app.provision.models import DriftReport, DriftStatus

        return DriftReport(
            status=DriftStatus.CHECK_FAILED,
            changes_detected=0,
            details=[
                "Scheduled drift skipped: no Terraform workspace for this deployment. "
                "Redeploy with Terraform or use a Boto3 deployment (detected via provision_engine)."
            ],
            checked_at=datetime.utcnow(),
        )

    return detect_drift(workspace, aws_credentials=aws_creds)


def scheduled_drift_check():
    """
    Celery Beat task: check all active deployments for drift.

    Uses each deployment owner's BYOC AWS credentials. Routes to boto3_drift or
    terraform plan per deployment provision_engine.
    """
    from app.database.mongo_client import get_database
    from app.provision.byoc_credentials import resolve_byoc_terraform_env
    from app.provision.models import DeploymentStatus, DriftReport, DriftStatus

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
        owner = deployment.get("user_id", "")
        config = deployment.get("config") or {}
        region = config.get("aws_region", "ap-south-1")

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
            drift_report = _run_scheduled_drift(deployment, aws_creds)

            if drift_report.status == DriftStatus.CHECK_FAILED and drift_report.details:
                detail0 = drift_report.details[0]
                if "Scheduled drift skipped" in detail0:
                    skipped += 1
                else:
                    checked += 1
            else:
                checked += 1

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
