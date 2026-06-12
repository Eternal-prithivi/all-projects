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
from app.byoc.gcp_bucket_helpers import (
    GCP_PRIMARY_LOCATION_DEFAULT,
    GCP_REPLICA_LOCATION_DEFAULT,
)
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


def get_gcp_byoc_record(username: str) -> Optional[Dict[str, Any]]:
    return byoc_collection.find_one(
        {"username": username, "csp": "GCP", "is_active": True}
    )


def get_azure_byoc_record(username: str) -> Optional[Dict[str, Any]]:
    return byoc_collection.find_one(
        {"username": username, "csp": "Azure", "is_active": True}
    )


def normalize_gcp_byoc_layout(record: Dict[str, Any]) -> Dict[str, Any]:
    storage = (
        record.get("storage_bucket_name")
        or record.get("bucket_name")
        or record.get("gcp_bucket_name")
        or ""
    ).strip()
    secure = (record.get("secure_bucket_name") or storage).strip()
    replica = (record.get("replica_bucket_name") or "").strip()
    primary_location = (
        record.get("gcp_primary_location")
        or record.get("primary_location")
        or GCP_PRIMARY_LOCATION_DEFAULT
    )
    replica_location = (
        record.get("gcp_replica_location")
        or record.get("replica_location")
        or GCP_REPLICA_LOCATION_DEFAULT
    )
    dual_write = record.get("secure_dual_write")
    if dual_write is None:
        dual_write = bool(replica)
    if not replica:
        dual_write = False
    return {
        "storage_bucket_name": storage,
        "secure_bucket_name": secure,
        "replica_bucket_name": replica,
        "primary_location": primary_location,
        "replica_location": replica_location,
        "secure_dual_write": bool(dual_write),
        "uses_dedicated_secure_bucket": bool(secure and secure != storage),
    }


def normalize_azure_byoc_layout(record: Dict[str, Any]) -> Dict[str, Any]:
    storage = (
        record.get("storage_container_name")
        or record.get("container_name")
        or ""
    ).strip()
    secure = (record.get("secure_container_name") or storage).strip()
    replica = (record.get("replica_container_name") or "").strip()
    dual_write = record.get("secure_dual_write")
    if dual_write is None:
        dual_write = bool(replica)
    if not replica:
        dual_write = False
    return {
        "storage_container_name": storage,
        "secure_container_name": secure,
        "replica_container_name": replica,
        "secure_dual_write": bool(dual_write),
        "uses_dedicated_secure_container": bool(secure and secure != storage),
    }


def get_gcp_bucket_layout(username: str) -> Optional[Dict[str, Any]]:
    record = get_gcp_byoc_record(username)
    if not record:
        return None
    return normalize_gcp_byoc_layout(record)


def get_azure_container_layout(username: str) -> Optional[Dict[str, Any]]:
    record = get_azure_byoc_record(username)
    if not record:
        return None
    return normalize_azure_byoc_layout(record)


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
    from app.cloud.providers import normalize_provider

    record = byoc_collection.find_one({
        "username": username,
        "csp": normalize_provider(csp),
        "is_active": True
    })
    
    if not record:
        return None
    
    # Decrypt the stored credentials
    encrypted_creds = record.get("credentials", {})
    decrypted = decrypt_credentials_dict(encrypted_creds)
    
    layout = None
    csp = record["csp"]
    if csp == "AWS":
        layout = normalize_aws_byoc_layout(record)
    elif csp == "GCP":
        layout = normalize_gcp_byoc_layout(record)
    elif csp == "Azure":
        layout = normalize_azure_byoc_layout(record)

    gcp_layout = layout if csp == "GCP" else {}
    az_layout = layout if csp == "Azure" else {}

    return {
        "csp": csp,
        "connection_method": record.get("connection_method", "access_keys"),
        "bucket_name": record.get("bucket_name", ""),
        "storage_bucket_name": (
            record.get("storage_bucket_name")
            or record.get("bucket_name")
            or gcp_layout.get("storage_bucket_name", "")
        ),
        "secure_bucket_name": (
            record.get("secure_bucket_name")
            or gcp_layout.get("secure_bucket_name", "")
        ),
        "replica_bucket_name": (
            record.get("replica_bucket_name")
            or gcp_layout.get("replica_bucket_name", "")
        ),
        "gcp_primary_location": record.get("gcp_primary_location", ""),
        "gcp_replica_location": record.get("gcp_replica_location", ""),
        "primary_region": record.get("primary_region", ""),
        "replica_region": record.get("replica_region", ""),
        "secure_dual_write": record.get("secure_dual_write", True),
        "container_name": record.get("container_name", ""),
        "storage_container_name": (
            record.get("storage_container_name")
            or record.get("container_name")
            or az_layout.get("storage_container_name", "")
        ),
        "secure_container_name": (
            record.get("secure_container_name")
            or az_layout.get("secure_container_name", "")
        ),
        "replica_container_name": (
            record.get("replica_container_name")
            or az_layout.get("replica_container_name", "")
        ),
        "account_name": record.get("account_name", ""),
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
        layout = get_gcp_bucket_layout(username) or {}
        storage_bucket = (
            layout.get("storage_bucket_name")
            or byoc.get("storage_bucket_name")
            or byoc.get("bucket_name")
            or settings.GCP_BUCKET_NAME
        )
        logger.info(f"BYOC: Using {username}'s own GCP credentials")
        return {
            "service_account_json": creds.get("service_account_json", ""),
            "bucket_name": storage_bucket,
            "billing_dataset_id": creds.get("billing_dataset_id", ""),
            "billing_table_id": creds.get("billing_table_id", ""),
            "is_byoc": True,
        }
    
    return {
        "service_account_key_path": settings.GCP_SERVICE_ACCOUNT_JSON_PATH,
        "bucket_name": settings.GCP_BUCKET_NAME,
        "billing_dataset_id": (settings.GCP_BILLING_DATASET_ID or "").strip(),
        "billing_table_id": (settings.GCP_BILLING_TABLE_ID or "").strip(),
        "is_byoc": False,
    }


def resolve_azure_credentials(username: str) -> Dict[str, str]:
    """
    Resolve Azure credentials — returns BYOC keys if configured, else Zenith defaults.
    """
    byoc = get_user_cloud_credentials(username, "Azure")
    
    if byoc:
        creds = byoc["credentials"]
        layout = get_azure_container_layout(username) or {}
        storage_container = (
            layout.get("storage_container_name")
            or byoc.get("storage_container_name")
            or byoc.get("container_name")
            or settings.AZURE_CONTAINER_NAME
        )
        logger.info(f"BYOC: Using {username}'s own Azure credentials")
        return {
            "account_name": creds.get("account_name", ""),
            "account_key": creds.get("account_key", ""),
            "container_name": storage_container,
            "subscription_id": (creds.get("subscription_id") or "").strip(),
            "tenant_id": (creds.get("tenant_id") or "").strip(),
            "client_id": (creds.get("client_id") or "").strip(),
            "client_secret": (creds.get("client_secret") or "").strip(),
            "resource_group": (creds.get("resource_group") or "").strip(),
            "location": (creds.get("location") or creds.get("azure_location") or "").strip(),
            "is_byoc": True,
        }
    
    return {
        "account_name": settings.AZURE_STORAGE_ACCOUNT_NAME,
        "account_key": settings.AZURE_STORAGE_ACCOUNT_KEY,
        "container_name": settings.AZURE_CONTAINER_NAME,
        "subscription_id": (settings.AZURE_SUBSCRIPTION_ID or "").strip(),
        "tenant_id": (settings.AZURE_TENANT_ID or "").strip(),
        "client_id": (settings.AZURE_CLIENT_ID or "").strip(),
        "client_secret": (settings.AZURE_CLIENT_SECRET or "").strip(),
        "resource_group": getattr(settings, "AZURE_RESOURCE_GROUP", "zenith-rg"),
        "location": getattr(settings, "AZURE_LOCATION", "eastus"),
        "is_byoc": False,
    }


def resolve_platform_storage_target(
    username: str,
    csp: str,
    *,
    region_slug: Optional[str] = None,
    bucket: Optional[str] = None,
    cloud_region: Optional[str] = None,
    account_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Platform-mode storage destination from catalog (None when BYOC or no catalog match).
    """
    csp_u = (csp or "").strip().upper()
    if csp_u == "AWS" and resolve_aws_credentials(username).get("is_byoc"):
        return None
    if csp_u == "GCP" and resolve_gcp_credentials(username).get("is_byoc"):
        return None
    if csp_u == "Azure" and resolve_azure_credentials(username).get("is_byoc"):
        return None

    from app.cloud.platform_storage_catalog import (
        resolve_platform_destination,
        resolve_platform_destination_by_bucket,
    )

    if region_slug:
        return resolve_platform_destination(csp_u, region_slug)
    if bucket:
        return resolve_platform_destination_by_bucket(
            csp_u,
            bucket,
            cloud_region=cloud_region,
            account_name=account_name,
        )
    return resolve_platform_destination(csp_u, region_slug)


def resolve_credentials(username: str, provider: str = "aws") -> Optional[Dict[str, Any]]:
    """
    Resolve credentials for infrastructure provisioning (Terraform subprocess).

    Returns None when BYOC is not configured for the provider. Does not include
    platform fallback credentials — callers may use server env when this returns None.
    """
    from app.cloud.providers import normalize_provider_key
    from app.provision.byoc_credentials import (
        resolve_azure_terraform_env,
        resolve_byoc_terraform_env,
        resolve_gcp_terraform_env,
        terraform_azure_env_to_api,
        terraform_env_to_api_credentials,
        terraform_gcp_env_to_api,
    )

    key = normalize_provider_key(provider)
    if key == "aws":
        env = resolve_byoc_terraform_env(username)
        return terraform_env_to_api_credentials(env)
    if key == "gcp":
        env = resolve_gcp_terraform_env(username)
        return terraform_gcp_env_to_api(env)
    if key == "azure":
        env = resolve_azure_terraform_env(username)
        return terraform_azure_env_to_api(env)
    return None


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
