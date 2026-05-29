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
    Build AWS environment variables for Terraform from the user's BYOC config.

    Returns an empty dict when the user has no active BYOC AWS connection.
    Does not fall back to Zenith platform credentials.
    """
    try:
        byoc = _fetch_byoc_aws_record(username)
        if not byoc:
            return {}

        creds = byoc.get("credentials") or {}
        connection_method = (byoc.get("connection_method") or "access_keys").lower()
        aws_region = creds.get("region") or region

        if connection_method == "iam_role":
            from app.byoc.credential_resolver import resolve_aws_credentials

            resolved = resolve_aws_credentials(username)
            if not resolved.get("is_byoc"):
                return {}
            result = {
                "AWS_ACCESS_KEY_ID": resolved.get("access_key_id", ""),
                "AWS_SECRET_ACCESS_KEY": resolved.get("secret_access_key", ""),
                "AWS_DEFAULT_REGION": resolved.get("region", aws_region),
            }
            if resolved.get("session_token"):
                result["AWS_SESSION_TOKEN"] = resolved["session_token"]
            return result

        access_key = creds.get("access_key_id", "")
        secret_key = creds.get("secret_access_key", "")
        if not access_key or not secret_key:
            logger.warning("BYOC AWS access keys incomplete for %s", username)
            return {}

        return {
            "AWS_ACCESS_KEY_ID": access_key,
            "AWS_SECRET_ACCESS_KEY": secret_key,
            "AWS_DEFAULT_REGION": aws_region,
        }
    except Exception as exc:
        logger.warning("BYOC terraform env resolution failed for %s: %s", username, exc)
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
