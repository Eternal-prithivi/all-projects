# =============================================================================
# MODULE: provision/sdk_drift.py
# PURPOSE: Drift detection/remediation for GCP/Azure SDK deployments.
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from app.cloud.providers import normalize_provider
from app.provision.models import DriftReport, DriftStatus
from app.provision.sdk_composer import apply_sdk, enabled_sdk_modules
from app.provision.sdk_modules import (
    azure_cosmos,
    azure_monitor,
    azure_storage,
    azure_vm,
    azure_vnet,
    gcp_firestore,
    gcp_gce,
    gcp_gcs,
    gcp_monitoring,
    gcp_network,
    gcp_service_account,
)
from app.provision.sdk_modules.context import SdkDeployContext

logger = logging.getLogger(__name__)

_GCP_DRIFT: dict[str, Callable] = {
    "gcp_network": gcp_network.check_gcp_network_drift,
    "gce": gcp_gce.check_gce_drift,
    "gcp_service_account": gcp_service_account.check_gcp_service_account_drift,
    "gcp_monitoring": gcp_monitoring.check_gcp_monitoring_drift,
    "gcs": gcp_gcs.check_gcs_drift,
    "firestore": gcp_firestore.check_firestore_drift,
}

_AZURE_DRIFT: dict[str, Callable] = {
    "vnet": azure_vnet.check_vnet_drift,
    "azure_vm": azure_vm.check_azure_vm_drift,
    "azure_monitor": azure_monitor.check_azure_monitor_drift,
    "azure_storage": azure_storage.check_azure_storage_drift,
    "cosmos": azure_cosmos.check_cosmos_drift,
}


def detect_drift_sdk(
    config: dict,
    cloud_env: dict[str, str],
    sdk_context: Optional[dict] = None,
) -> DriftReport:
    ctx = SdkDeployContext.from_dict(sdk_context)
    csp = normalize_provider(config.get("csp") or "AWS")
    drift_map = _GCP_DRIFT if csp == "GCP" else _AZURE_DRIFT
    details: list[str] = []
    changes = 0

    try:
        for mod in enabled_sdk_modules(config):
            checker = drift_map.get(mod)
            if not checker:
                continue
            c, d = checker(config, cloud_env, ctx)
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
