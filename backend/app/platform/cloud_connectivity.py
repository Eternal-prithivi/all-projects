"""Platform-level tri-cloud credential probes (no auth, no live API calls)."""

from __future__ import annotations

from typing import Any, Dict

from app.utils.config import settings
from app.utils.gcp_credentials import gcp_credentials_file_present


def _status(configured: bool) -> str:
    return "configured" if configured else "not_configured"


def probe_platform_cloud_connectivity() -> Dict[str, Any]:
    """
    Summarize whether Zenith platform .env has enough fields for each CSP.
    Does not call cloud APIs — safe for public /api/platform/status.
    """
    aws_storage = bool(
        settings.AWS_ACCESS_KEY_ID
        and settings.AWS_SECRET_ACCESS_KEY
        and settings.S3_BUCKET_NAME
    )
    aws_billing = aws_storage  # Cost Explorer uses same IAM keys

    gcp_key = gcp_credentials_file_present()
    gcp_storage = bool(gcp_key and settings.GCP_BUCKET_NAME and settings.GCP_PROJECT_ID)
    gcp_billing = bool(
        gcp_key
        and settings.GCP_BILLING_DATASET_ID
        and settings.GCP_BILLING_TABLE_ID
    )

    azure_storage = bool(
        settings.AZURE_STORAGE_ACCOUNT_NAME
        and settings.AZURE_STORAGE_ACCOUNT_KEY
        and settings.AZURE_CONTAINER_NAME
    )
    azure_billing = bool(
        settings.AZURE_SUBSCRIPTION_ID
        and settings.AZURE_TENANT_ID
        and settings.AZURE_CLIENT_ID
        and settings.AZURE_CLIENT_SECRET
    )

    providers: Dict[str, Any] = {
        "aws": {
            "storage": _status(aws_storage),
            "billing": _status(aws_billing),
            "secure_vault": _status(bool(settings.SECURE_S3_BUCKET_NAME)),
            "provision": _status(aws_storage),
            "vm": _status(aws_storage),
        },
        "gcp": {
            "storage": _status(gcp_storage),
            "billing": _status(gcp_billing),
            "secure_vault": _status(gcp_storage),
            "provision": _status(gcp_storage),
            "vm": _status(gcp_storage),
        },
        "azure": {
            "storage": _status(azure_storage),
            "billing": _status(azure_billing),
            "secure_vault": _status(azure_storage),
            "provision": _status(azure_storage),
            "vm": "not_supported",  # DEC-026 / VM scope doc — Azure Compute deferred
        },
    }

    configured_count = sum(
        1
        for p in providers.values()
        if p.get("storage") == "configured"
    )

    return {
        "providers": providers,
        "summary": {
            "storage_ready_count": configured_count,
            "total_providers": 3,
            "any_storage_ready": configured_count >= 1,
        },
    }
