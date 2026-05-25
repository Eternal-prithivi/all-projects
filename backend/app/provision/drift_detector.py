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

from pydantic import BaseModel

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


class RemediationResult(BaseModel):
    """Outcome of a drift remediation attempt."""
    success: bool = False
    performed: bool = False
    message: str = ""
    plan_output: str = ""
    apply_output: str = ""


def remediate_drift(
    workspace_dir: str,
    aws_credentials: Optional[dict] = None,
    check_only: bool = True,
) -> RemediationResult:
    """
    Remediate detected drift by re-applying the Terraform configuration.

    Adapted from aws-provision-using-terraform/drift-detection/remediation.py.

    By default (check_only=True), runs ``terraform plan`` to show what would
    change WITHOUT actually applying. Set ``check_only=False`` to run
    ``terraform apply --auto-approve`` and restore desired state.

    Args:
        workspace_dir: Path to the Terraform workspace with state files.
        aws_credentials: AWS env vars for Terraform subprocess.
        check_only: If True, only show plan — do not apply.

    Returns:
        RemediationResult with success/performed flags and output text.
    """
    runner = TerraformRunner(workspace_dir, aws_credentials)

    try:
        # Step 1: terraform init (ensure plugins are ready)
        init_result = runner.init()
        if not init_result["success"]:
            return RemediationResult(
                success=False,
                performed=False,
                message="terraform init failed during remediation.",
                plan_output=init_result.get("error", ""),
            )

        # Step 2: terraform plan (see what would change)
        plan_result = runner.plan()
        plan_output = plan_result.get("output", "")

        if not plan_result.get("has_changes", True):
            return RemediationResult(
                success=True,
                performed=False,
                message="No drift detected — infrastructure matches desired state.",
                plan_output=plan_output,
            )

        if check_only:
            return RemediationResult(
                success=True,
                performed=False,
                message="Drift remediation plan generated (check-only mode). Review output before applying.",
                plan_output=plan_output,
            )

        # Step 3: terraform apply (only if check_only=False)
        apply_result = runner.apply()
        if not apply_result["success"]:
            return RemediationResult(
                success=False,
                performed=True,
                message="terraform apply failed during remediation.",
                plan_output=plan_output,
                apply_output=apply_result.get("error", ""),
            )

        return RemediationResult(
            success=True,
            performed=True,
            message="Drift remediated successfully — infrastructure restored to desired state.",
            plan_output=plan_output,
            apply_output=apply_result.get("output", ""),
        )

    except Exception as e:
        logger.error(f"Drift remediation failed: {e}")
        return RemediationResult(
            success=False,
            performed=False,
            message=f"Remediation error: {str(e)}",
        )
