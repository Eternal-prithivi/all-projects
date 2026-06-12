# =============================================================================
# MODULE: provision/byoc_credentials.py
# PURPOSE: Resolve BYOC AWS credentials as Terraform subprocess env vars
# USED BY: routes_provision.py, tasks.py (scheduled drift)
# DO NOT:
#   - Fall back to platform AWS credentials for background drift checks
#   - Return credentials in API responses — env dict is for subprocess only
# =============================================================================
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _fetch_byoc_aws_record(username: str) -> Optional[dict[str, Any]]:
    """Load active BYOC AWS record for a user (lazy import for testability)."""
    from app.byoc.credential_resolver import get_user_cloud_credentials

    return get_user_cloud_credentials(username, "AWS")


def resolve_byoc_terraform_env(username: str, region: str = "ap-south-1") -> dict[str, str]:
    """
    Build AWS environment variables for Terraform/Boto3 provision paths.

    Uses BYOC when connected; otherwise falls back to Zenith platform AWS keys
    (same routing as storage and VM).
    """
    try:
        from app.byoc.credential_resolver import resolve_aws_credentials

        resolved = resolve_aws_credentials(username)
        access_key = (resolved.get("access_key_id") or "").strip()
        secret_key = (resolved.get("secret_access_key") or "").strip()
        if not access_key or not secret_key:
            return {}
        result = {
            "AWS_ACCESS_KEY_ID": access_key,
            "AWS_SECRET_ACCESS_KEY": secret_key,
            "AWS_DEFAULT_REGION": resolved.get("region") or region,
        }
        if resolved.get("session_token"):
            result["AWS_SESSION_TOKEN"] = resolved["session_token"]
        return result
    except Exception as exc:
        logger.warning("AWS provision env resolution failed for %s: %s", username, exc)
        return {}


def terraform_env_to_api_credentials(env: dict[str, str]) -> Optional[dict[str, Any]]:
    """Map Terraform env dict to the shape expected by legacy resolve_credentials callers."""
    if not env.get("AWS_ACCESS_KEY_ID"):
        return None
    out: dict[str, Any] = {
        "access_key_id": env["AWS_ACCESS_KEY_ID"],
        "secret_access_key": env.get("AWS_SECRET_ACCESS_KEY", ""),
    }
    if env.get("AWS_SESSION_TOKEN"):
        out["session_token"] = env["AWS_SESSION_TOKEN"]
    return out


def resolve_gcp_terraform_env(username: str) -> dict[str, str]:
    """Build GCP env vars from BYOC service account JSON or platform key file."""
    import json as _json
    from pathlib import Path

    from app.byoc.credential_resolver import resolve_gcp_credentials
    from app.utils.config import settings

    gcp = resolve_gcp_credentials(username)
    sa_info = None

    if gcp.get("is_byoc"):
        sa_raw = (gcp.get("service_account_json") or "").strip()
        if sa_raw:
            try:
                sa_info = _json.loads(sa_raw) if isinstance(sa_raw, str) else sa_raw
            except _json.JSONDecodeError:
                logger.warning("Invalid GCP SA JSON for %s", username)
                return {}
    else:
        key_path = (gcp.get("service_account_key_path") or settings.GCP_SERVICE_ACCOUNT_JSON_PATH or "").strip()
        if key_path and Path(key_path).is_file():
            try:
                sa_info = _json.loads(Path(key_path).read_text(encoding="utf-8"))
            except (_json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read platform GCP key for %s: %s", username, exc)
                return {}

    if not sa_info:
        return {}
    return {
        "GOOGLE_CREDENTIALS": _json.dumps(sa_info),
        "GOOGLE_PROJECT": sa_info.get("project_id", "") or (settings.GCP_PROJECT_ID or ""),
    }


def resolve_azure_terraform_env(username: str) -> dict[str, str]:
    """Build Azure ARM env vars from BYOC or platform service principal."""
    from app.byoc.credential_resolver import resolve_azure_credentials

    az = resolve_azure_credentials(username)
    subscription_id = (az.get("subscription_id") or "").strip()
    tenant_id = (az.get("tenant_id") or "").strip()
    client_id = (az.get("client_id") or "").strip()
    client_secret = (az.get("client_secret") or "").strip()
    if not all([subscription_id, tenant_id, client_id, client_secret]):
        logger.warning("Azure provision credentials incomplete for %s", username)
        return {}
    return {
        "ARM_SUBSCRIPTION_ID": subscription_id,
        "ARM_TENANT_ID": tenant_id,
        "ARM_CLIENT_ID": client_id,
        "ARM_CLIENT_SECRET": client_secret,
    }


def _fetch_byoc_gcp_record(username: str) -> Optional[dict[str, Any]]:
    from app.byoc.credential_resolver import get_user_cloud_credentials

    return get_user_cloud_credentials(username, "GCP")


def _fetch_byoc_azure_record(username: str) -> Optional[dict[str, Any]]:
    from app.byoc.credential_resolver import get_user_cloud_credentials

    return get_user_cloud_credentials(username, "Azure")


def terraform_gcp_env_to_api(env: dict[str, str]) -> Optional[dict[str, Any]]:
    if not env.get("GOOGLE_CREDENTIALS"):
        return None
    return {
        "service_account_json": env["GOOGLE_CREDENTIALS"],
        "project_id": env.get("GOOGLE_PROJECT", ""),
    }


def resolve_provision_terraform_env(
    username: str,
    csp: str,
    region: str = "ap-south-1",
) -> tuple[dict[str, str], Optional[str]]:
    """
    Build full Terraform subprocess environment for AWS, GCP, or Azure BYOC.

    Returns (env_dict, error_message). error_message is set when required creds are missing.
    """
    from app.cloud.providers import normalize_provider

    provider = normalize_provider(csp)
    if provider == "AWS":
        env = resolve_byoc_terraform_env(username, region)
        if not env.get("AWS_ACCESS_KEY_ID"):
            return {}, (
                "No AWS credentials for provisioning. Connect AWS under Settings (BYOC) "
                "or configure platform AWS keys on the server."
            )
        return env, None
    if provider == "GCP":
        env = resolve_gcp_terraform_env(username)
        if not env.get("GOOGLE_CREDENTIALS"):
            return {}, (
                "No GCP credentials for provisioning. Connect GCP under Settings (BYOC) "
                "or configure the platform GCP service account on the server."
            )
        return env, None
    env = resolve_azure_terraform_env(username)
    if not env.get("ARM_CLIENT_ID"):
        return {}, (
            "No Azure credentials for provisioning. Connect Azure under Settings (BYOC) "
            "or configure platform Azure service principal keys on the server."
        )
    return env, None


def terraform_azure_env_to_api(env: dict[str, str]) -> Optional[dict[str, Any]]:
    if not env.get("ARM_CLIENT_ID"):
        return None
    return {
        "subscription_id": env.get("ARM_SUBSCRIPTION_ID", ""),
        "tenant_id": env.get("ARM_TENANT_ID", ""),
        "client_id": env.get("ARM_CLIENT_ID", ""),
        "client_secret": env.get("ARM_CLIENT_SECRET", ""),
    }
