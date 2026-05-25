# =============================================================================
# MODULE: provision/drift_detector.py
# PURPOSE: Detect unauthorized changes to deployed Terraform resources
# USED BY: routes_provision.py (on-demand drift check), tasks.py (scheduled)
# DEPENDS ON: terraform_runner.py for workspace execution
# DO NOT:
#   - Run drift checks on deployments with status != DEPLOYED
#   - Remove the drift history — it's valuable audit data
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.provision.models import DriftReport, DriftStatus
from app.provision.terraform_runner import TerraformRunner

logger = logging.getLogger(__name__)


def detect_drift(
    workspace_dir: str,
    aws_credentials: Optional[dict] = None,
) -> DriftReport:
    """
    Run terraform plan on an existing deployment to detect configuration drift.

    Drift = any difference between the real AWS state and the Terraform state file.
    Returns a DriftReport with status, change count, and details.
    """
    runner = TerraformRunner(workspace_dir, aws_credentials)

    try:
        plan_result = runner.plan()

        if not plan_result["success"]:
            return DriftReport(
                status=DriftStatus.CHECK_FAILED,
                changes_detected=0,
                details=[plan_result.get("error", "Plan command failed")],
                checked_at=datetime.utcnow(),
            )

        output = plan_result.get("output", "")

        # Parse terraform plan output for drift indicators
        if "No changes." in output or "Your infrastructure matches the configuration" in output:
            return DriftReport(
                status=DriftStatus.CLEAN,
                changes_detected=0,
                details=["Infrastructure matches Terraform state — no drift detected."],
                checked_at=datetime.utcnow(),
            )

        # Count changes from plan output
        changes = 0
        change_details: list[str] = []

        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("~ ") or stripped.startswith("+ ") or stripped.startswith("- "):
                changes += 1
                if len(change_details) < 20:  # Cap detail lines
                    change_details.append(stripped)

        # Look for the summary line like "Plan: 0 to add, 2 to change, 0 to destroy."
        for line in output.split("\n"):
            if "Plan:" in line and "to add" in line:
                change_details.insert(0, line.strip())
                break

        if changes > 0 or plan_result.get("has_changes", False):
            return DriftReport(
                status=DriftStatus.DRIFT_DETECTED,
                changes_detected=max(changes, 1),
                details=change_details if change_details else ["Changes detected — review terraform plan output."],
                checked_at=datetime.utcnow(),
            )

        return DriftReport(
            status=DriftStatus.CLEAN,
            changes_detected=0,
            details=["No drift detected."],
            checked_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Drift detection failed: {e}")
        return DriftReport(
            status=DriftStatus.CHECK_FAILED,
            changes_detected=0,
            details=[f"Drift check error: {str(e)}"],
            checked_at=datetime.utcnow(),
        )
