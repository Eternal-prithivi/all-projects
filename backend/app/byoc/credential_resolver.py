# =============================================================================
# MODULE: byoc/credential_resolver.py  (192 lines)
# PURPOSE: Decides which credentials to use for a given user — BYOC or Zenith platform defaults
#   - resolve_aws_credentials(username) → returns dict with access_key, secret_key, bucket_name, is_byoc
#   - All storage uploads/downloads call this FIRST to know which S3 to use
# READS FROM:  byoc_credentials collection
# CALLED BY:   routes_storage.py (sync, upload), uploader.py, manager.py
# DO NOT:
#   - Return plaintext credentials in API responses — only use internally
#   - Cache credentials in memory without TTL — they may be revoked
#   - Fall back to platform creds silently if BYOC is configured but invalid
# =============================================================================
"""
or the user's own BYOC credentials for each operation.
"""

from typing import Optional, Dict, Any
from app.database.mongo_client import get_database
from app.byoc.aws_bucket_helpers import REPLICA_REGION_DEFAULT
from app.byoc.encryption import decrypt_credentials_dict
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

DB = get_database()
byoc_collection = DB["byoc_credentials"]

def _get_default_aws_bucket_name() -> str:
    regular_bucket = getattr(settings, "REGULAR_S3_BUCKET_NAME", None)
    if regular_bucket:
        return regular_bucket
    return settings.S3_BUCKET_NAME


def get_aws_byoc_record(username: str) -> Optional[Dict[str, Any]]:
    """Active AWS BYOC Mongo record (not decrypted)."""
    return byoc_collection.find_one(
        {"username": username, "csp": "AWS", "is_active": True}
    )


def normalize_aws_byoc_layout(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical BYOC bucket layout from Mongo record (supports legacy single-bucket rows).
    """
    storage = (record.get("storage_bucket_name") or record.get("bucket_name") or "").strip()
    secure = (record.get("secure_bucket_name") or storage).strip()
    replica = (record.get("replica_bucket_name") or "").strip()
    primary_region = (
        record.get("primary_region")
        or record.get("region")
        or creds_region(record)
    )
    replica_region = REPLICA_REGION_DEFAULT if replica else ""
    dual_write = record.get("secure_dual_write")
    if dual_write is None:
        dual_write = bool(replica)
    if not replica:
        dual_write = False
    return {
        "storage_bucket_name": storage,
        "secure_bucket_name": secure,
        "replica_bucket_name": replica,
        "primary_region": primary_region,
        "replica_region": replica_region,
        "secure_dual_write": bool(dual_write),
        "uses_dedicated_secure_bucket": bool(secure and secure != storage),
    }


def get_aws_bucket_layout(username: str) -> Optional[Dict[str, Any]]:
    """Resolved bucket names and regions for AWS BYOC."""
    record = get_aws_byoc_record(username)
    if not record:
        return None
    return normalize_aws_byoc_layout(record)


def get_user_cloud_credentials(username: str, csp: str) -> Optional[Dict[str, Any]]:
    """
    Get cloud credentials for a user + CSP.
    Returns decrypted credentials if BYOC is configured, None otherwise.
    
    Args:
        username: The user's username
        csp: Cloud provider — "AWS", "GCP", or "Azure"
    
    Returns:
        Dict with decrypted credentials, or None if no BYOC config.
    """
    record = byoc_collection.find_one({
        "username": username,
        "csp": csp.upper(),
        "is_active": True
    })
    
    if not record:
        return None
    
    # Decrypt the stored credentials
    encrypted_creds = record.get("credentials", {})
    decrypted = decrypt_credentials_dict(encrypted_creds)
    
    layout = None
    if record["csp"] == "AWS":
        storage = record.get("storage_bucket_name") or record.get("bucket_name") or ""
        layout = {
            "storage_bucket_name": storage,
            "secure_bucket_name": record.get("secure_bucket_name") or storage,
            "replica_bucket_name": record.get("replica_bucket_name") or "",
        }

    return {
        "csp": record["csp"],
        "connection_method": record.get("connection_method", "access_keys"),
        "bucket_name": record.get("bucket_name", ""),
        "storage_bucket_name": record.get("storage_bucket_name", record.get("bucket_name", "")),
        "secure_bucket_name": record.get("secure_bucket_name", ""),
        "replica_bucket_name": record.get("replica_bucket_name", ""),
        "primary_region": record.get("primary_region", ""),
        "replica_region": record.get("replica_region", ""),
        "secure_dual_write": record.get("secure_dual_write", True),
        "container_name": record.get("container_name", ""),
        "credentials": decrypted,
        "is_active": record.get("is_active", True),
        "layout": layout,
    }


def resolve_aws_credentials(username: str) -> Dict[str, str]:
    """
    Resolve AWS credentials — returns BYOC keys if configured, else Zenith defaults.
    
    Returns:
        Dict with keys: access_key_id, secret_access_key, bucket_name
    """
    byoc = get_user_cloud_credentials(username, "AWS")
    
    if byoc:
        creds = byoc["credentials"]
        connection_method = (byoc.get("connection_method") or "access_keys").lower()
        bucket_name = (
            byoc.get("storage_bucket_name")
            or byoc.get("bucket_name")
            or _get_default_aws_bucket_name()
        )
        region = (
            creds.get("region")
            or byoc.get("primary_region")
            or settings.PRIMARY_S3_REGION
        )

        if connection_method == "iam_role":
            role_arn = creds.get("role_arn", "")
            external_id = creds.get("external_id", "")
            if not role_arn or not external_id:
                raise ValueError("BYOC AWS IAM Role credentials are missing role_arn or external_id")

            logger.info(f"BYOC: Assuming {username}'s AWS IAM role for temporary credentials")
            import boto3

            sts = boto3.client(
                "sts",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=region,
            )
            resp = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=f"zenith-byoc-{username}",
                ExternalId=external_id,
                DurationSeconds=3600,
            )
            temp = resp["Credentials"]
            return {
                "access_key_id": temp["AccessKeyId"],
                "secret_access_key": temp["SecretAccessKey"],
                "session_token": temp["SessionToken"],
                "bucket_name": bucket_name,
                "region": region,
                "is_byoc": True,
                "connection_method": "iam_role",
            }

        logger.info(f"BYOC: Using {username}'s own AWS access keys")
        return {
            "access_key_id": creds.get("access_key_id", ""),
            "secret_access_key": creds.get("secret_access_key", ""),
            "bucket_name": bucket_name,
            "region": region,
            "is_byoc": True,
            "connection_method": "access_keys",
        }
    
    return {
        "access_key_id": settings.AWS_ACCESS_KEY_ID,
        "secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "bucket_name": _get_default_aws_bucket_name(),
        "region": settings.PRIMARY_S3_REGION,
        "is_byoc": False,
        "connection_method": "platform",
    }


def resolve_gcp_credentials(username: str) -> Dict[str, str]:
    """
    Resolve GCP credentials — returns BYOC keys if configured, else Zenith defaults.
    """
    byoc = get_user_cloud_credentials(username, "GCP")
    
    if byoc:
        creds = byoc["credentials"]
        logger.info(f"BYOC: Using {username}'s own GCP credentials")
        return {
            "service_account_json": creds.get("service_account_json", ""),
            "bucket_name": byoc.get("bucket_name", settings.GCP_BUCKET_NAME),
            "is_byoc": True,
        }
    
    return {
        "service_account_key_path": settings.GCP_SERVICE_ACCOUNT_JSON_PATH,
        "bucket_name": settings.GCP_BUCKET_NAME,
        "is_byoc": False,
    }


def resolve_azure_credentials(username: str) -> Dict[str, str]:
    """
    Resolve Azure credentials — returns BYOC keys if configured, else Zenith defaults.
    """
    byoc = get_user_cloud_credentials(username, "Azure")
    
    if byoc:
        creds = byoc["credentials"]
        logger.info(f"BYOC: Using {username}'s own Azure credentials")
        return {
            "account_name": creds.get("account_name", ""),
            "account_key": creds.get("account_key", ""),
            "container_name": byoc.get("container_name", settings.AZURE_CONTAINER_NAME),
            "is_byoc": True,
        }
    
    return {
        "account_name": settings.AZURE_STORAGE_ACCOUNT_NAME,
        "account_key": settings.AZURE_STORAGE_ACCOUNT_KEY,
        "container_name": settings.AZURE_CONTAINER_NAME,
        "is_byoc": False,
    }


def resolve_credentials(username: str, provider: str = "aws") -> Optional[Dict[str, Any]]:
    """
    Resolve credentials for infrastructure provisioning (Terraform subprocess).

    Returns None when BYOC is not configured for the provider. Does not include
    platform fallback credentials — callers may use server env when this returns None.
    """
    if provider.lower() != "aws":
        return None
    from app.provision.byoc_credentials import (
        resolve_byoc_terraform_env,
        terraform_env_to_api_credentials,
    )

    env = resolve_byoc_terraform_env(username)
    return terraform_env_to_api_credentials(env)


def get_byoc_status(username: str) -> Dict[str, Any]:
    """
    Get BYOC status for all CSPs for a user.
    Returns which clouds have BYOC configured.
    """
    status = {}
    for csp in ["AWS", "GCP", "Azure"]:
        record = byoc_collection.find_one({
            "username": username,
            "csp": csp,
            "is_active": True
        })
        entry = {
            "connected": record is not None,
            "connection_method": record.get("connection_method", None) if record else None,
            "bucket_name": record.get("bucket_name", record.get("container_name", "")) if record else "",
            "connected_at": record.get("created_at", None) if record else None,
        }
        if record and csp == "AWS":
            layout = normalize_aws_byoc_layout(record)
            entry.update({**layout, "bucket_name": layout["storage_bucket_name"]})
        status[csp.lower()] = entry
    return status


def creds_region(record: dict) -> str:
    enc = record.get("credentials") or {}
    try:
        dec = decrypt_credentials_dict(enc) if enc else {}
        return dec.get("region") or settings.PRIMARY_S3_REGION
    except Exception:
        return settings.PRIMARY_S3_REGION
