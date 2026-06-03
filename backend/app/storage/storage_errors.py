"""Structured HTTP errors for storage credential / config gaps."""

from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException

from app.cloud.providers import CloudProvider, normalize_provider_key


def missing_storage_config(
    provider: str,
    message: str,
    setup_steps: Optional[List[str]] = None,
    *,
    status_code: int = 400,
) -> HTTPException:
    key = normalize_provider_key(provider)
    steps = setup_steps or _default_setup_steps(key)
    return HTTPException(
        status_code=status_code,
        detail={
            "status": "missing_config",
            "provider": key,
            "message": message,
            "setup_steps": steps,
        },
    )


def restore_not_supported(provider: CloudProvider) -> HTTPException:
    key = normalize_provider_key(provider)
    return HTTPException(
        status_code=501,
        detail={
            "status": "not_supported",
            "provider": key,
            "message": (
                f"Archive restore for {provider} is not implemented yet. "
                "Use your cloud console or wait for a future Zenith release."
            ),
            "setup_steps": [
                "AWS Glacier/S3 restore is available via POST /api/storage/restore/AWS/{filename}",
                "GCP Archive and Azure Archive restore: planned in a later parity phase",
            ],
        },
    )


def _default_setup_steps(provider_key: str) -> List[str]:
    if provider_key == "gcp":
        return [
            "Connect GCP under BYOC (service account + bucket), or set GCP_SERVICE_ACCOUNT_JSON_PATH and GCP_BUCKET_NAME in backend .env",
            "See docs/cloud/CREDENTIAL_CONTRACT.md and docs/setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md",
        ]
    if provider_key == "azure":
        return [
            "Connect Azure under BYOC (account + key + container), or set AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY, and AZURE_STORAGE_CONTAINER_NAME in backend .env",
            "See docs/cloud/CREDENTIAL_CONTRACT.md",
        ]
    return [
        "Connect AWS under BYOC or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3 bucket names in backend .env",
        "See docs/setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md",
    ]


def validate_gcp_storage_ready(gcp: dict) -> Optional[HTTPException]:
    bucket = (gcp.get("bucket_name") or "").strip()
    if not bucket:
        return missing_storage_config("GCP", "GCP bucket not configured.")
    if gcp.get("is_byoc"):
        if not (gcp.get("service_account_json") or "").strip():
            return missing_storage_config(
                "GCP",
                "GCP BYOC is connected but service account JSON is missing.",
            )
    elif not (gcp.get("service_account_key_path") or "").strip():
        return missing_storage_config(
            "GCP",
            "GCP platform storage is not configured (service account path missing).",
        )
    return None


def validate_azure_storage_ready(azure: dict) -> Optional[HTTPException]:
    container = (azure.get("container_name") or "").strip()
    if not container:
        return missing_storage_config("Azure", "Azure container not configured.")
    account = (azure.get("account_name") or "").strip()
    key = (azure.get("account_key") or "").strip()
    if not account or not key:
        return missing_storage_config(
            "Azure",
            "Azure storage account name and key are required.",
        )
    return None
