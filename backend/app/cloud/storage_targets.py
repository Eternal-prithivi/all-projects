"""Per-provider storage / secure-vault destination metadata for UI banners."""

from __future__ import annotations

from typing import Any, Dict, List

from app.byoc.credential_resolver import get_aws_bucket_layout
from app.byoc.credential_resolver import resolve_azure_credentials, resolve_gcp_credentials
from app.cloud.availability import CloudFeature, available_providers, credential_source
from app.cloud.providers import CloudProvider
from app.storage.secure_vault import resolve_secure_storage
from app.utils.config import settings


def _aws_targets(username: str) -> Dict[str, Any]:
    layout = get_aws_bucket_layout(username)
    src = credential_source(username, "AWS")
    if layout:
        storage_bucket = layout["storage_bucket_name"]
        secure_bucket = layout["secure_bucket_name"]
        region = layout["primary_region"]
        secure_prefix = (
            f"{username}/"
            if layout.get("uses_dedicated_secure_bucket")
            else f"secure/{username}/"
        )
    else:
        storage_bucket = getattr(
            settings, "REGULAR_S3_BUCKET_NAME", settings.S3_BUCKET_NAME
        )
        secure_bucket = settings.SECURE_S3_BUCKET_NAME
        region = settings.PRIMARY_S3_REGION
        secure_prefix = f"{username}/"
    storage = {
        "bucket": storage_bucket,
        "region": region,
        "key_prefix": f"{username}/",
    }
    security = {
        "bucket": secure_bucket,
        "region": region,
        "key_prefix": secure_prefix,
        "replica_bucket": (layout or {}).get("replica_bucket_name") or settings.REPLICA_S3_BUCKET_NAME,
        "replica_region": (layout or {}).get("replica_region") or settings.REPLICA_S3_REGION,
        "secure_dual_write": bool((layout or {}).get("secure_dual_write", True)),
    }
    return {
        "csp": "AWS",
        "credential_source": src,
        "storage": storage,
        "security": security,
    }


def _gcp_targets(username: str) -> Dict[str, Any]:
    gcp = resolve_gcp_credentials(username)
    bucket = gcp.get("bucket_name") or settings.GCP_BUCKET_NAME
    try:
        secure = resolve_secure_storage(username, "GCP")
        secure_bucket = secure.bucket_name
        secure_prefix = secure.object_key(username, "").rstrip("/") + "/"
    except Exception:
        secure_bucket = bucket
        secure_prefix = f"secure/{username}/"
    return {
        "csp": "GCP",
        "credential_source": credential_source(username, "GCP"),
        "storage": {
            "bucket": bucket,
            "region": settings.GCP_ZONE or "—",
            "key_prefix": f"{username}/",
        },
        "security": {
            "bucket": secure_bucket,
            "region": settings.GCP_ZONE or "—",
            "key_prefix": secure_prefix,
            "replica_bucket": None,
            "replica_region": None,
            "secure_dual_write": False,
        },
    }


def _azure_targets(username: str) -> Dict[str, Any]:
    az = resolve_azure_credentials(username)
    container = az.get("container_name") or settings.AZURE_CONTAINER_NAME
    account = az.get("account_name") or settings.AZURE_STORAGE_ACCOUNT_NAME
    try:
        secure = resolve_secure_storage(username, "Azure")
        secure_container = secure.container_name
        secure_prefix = secure.object_key(username, "").rstrip("/") + "/"
    except Exception:
        secure_container = container
        secure_prefix = f"secure/{username}/"
    return {
        "csp": "Azure",
        "credential_source": credential_source(username, "Azure"),
        "storage": {
            "bucket": container,
            "account": account,
            "region": "—",
            "key_prefix": f"{username}/",
        },
        "security": {
            "bucket": secure_container,
            "account": account,
            "region": "—",
            "key_prefix": secure_prefix,
            "replica_bucket": None,
            "replica_region": None,
            "secure_dual_write": False,
        },
    }


def build_storage_targets_payload(username: str) -> Dict[str, Any]:
    """Multi-cloud destinations for Storage / Security banners."""
    providers: List[CloudProvider] = available_providers(username, CloudFeature.STORAGE)
    by_csp: Dict[str, Any] = {}
    for p in providers:
        if p == "AWS":
            by_csp[p] = _aws_targets(username, "storage")
        elif p == "GCP":
            by_csp[p] = _gcp_targets(username)
        else:
            by_csp[p] = _azure_targets(username)

    has_byoc = any(t["credential_source"] == "byoc" for t in by_csp.values())
    has_platform = any(t["credential_source"] == "platform" for t in by_csp.values())
    if has_byoc and has_platform:
        mode = "hybrid"
    elif has_byoc:
        mode = "byoc"
    else:
        mode = "platform"

    return {
        "mode": mode,
        "providers": providers,
        "targets": by_csp,
    }
