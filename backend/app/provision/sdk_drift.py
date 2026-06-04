# =============================================================================
# MODULE: provision/sdk_drift.py
# PURPOSE: Drift detection/remediation for GCP/Azure SDK deployments.
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.cloud.providers import normalize_provider
from app.provision.models import DriftReport, DriftStatus
from app.provision.sdk_composer import apply_sdk, enabled_sdk_modules
from app.provision.sdk_modules import azure_storage, gcp_gcs
from app.provision.sdk_modules.context import SdkDeployContext

logger = logging.getLogger(__name__)


def detect_drift_sdk(
    config: dict,
    cloud_env: dict[str, str],
    sdk_context: Optional[dict] = None,
) -> DriftReport:
    ctx = SdkDeployContext.from_dict(sdk_context)
    csp = normalize_provider(config.get("csp") or "AWS")
    details: list[str] = []
    changes = 0

    try:
        for mod in enabled_sdk_modules(config):
            if mod == "gcs":
                c, d = gcp_gcs.check_gcs_drift(config, cloud_env, ctx)
            else:
                c, d = azure_storage.check_azure_storage_drift(config, cloud_env, ctx)
            changes += c
            details.extend(d)

        if changes > 0:
            return DriftReport(
                status=DriftStatus.DRIFT_DETECTED,
                changes_detected=changes,
                details=details[:20],
                checked_at=datetime.utcnow(),
            )
        return DriftReport(
            status=DriftStatus.CLEAN,
            changes_detected=0,
            details=[f"Infrastructure matches saved configuration — no drift ({csp} SDK)."],
            checked_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("SDK drift check failed")
        return DriftReport(
            status=DriftStatus.CHECK_FAILED,
            changes_detected=0,
            details=[str(exc)],
            checked_at=datetime.utcnow(),
        )


def remediate_drift_sdk(
    config: dict,
    cloud_env: dict[str, str],
    sdk_context: Optional[dict] = None,
    check_only: bool = True,
) -> dict[str, Any]:
    if check_only:
        report = detect_drift_sdk(config, cloud_env, sdk_context)
        if report.status == DriftStatus.CLEAN:
            return {
                "success": True,
                "performed": False,
                "message": "No drift detected — infrastructure matches desired state.",
                "plan_output": "\n".join(report.details),
            }
        return {
            "success": True,
            "performed": False,
            "message": "Drift detected. Set check_only=false to re-apply SDK configuration.",
            "plan_output": "\n".join(report.details),
        }

    result = apply_sdk(config, cloud_env, sdk_context)
    return {
        "success": result.get("success", False),
        "performed": True,
        "message": "SDK re-apply finished." if result.get("success") else result.get("error"),
        "plan_output": result.get("output", ""),
        "apply_output": result.get("output", ""),
        "sdk_context": result.get("sdk_context"),
    }
