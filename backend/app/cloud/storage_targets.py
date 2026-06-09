"""Per-provider storage / secure-vault destination metadata for UI banners."""

from __future__ import annotations

from typing import Any, Dict, List

from app.byoc.credential_resolver import (
    get_aws_bucket_layout,
    get_azure_container_layout,
    get_gcp_bucket_layout,
    resolve_aws_credentials,
    resolve_azure_credentials,
    resolve_gcp_credentials,
)
from app.cloud.platform_storage_catalog import (
    catalog_is_multi_region,
    get_platform_buckets_for_csp,
)
from app.cloud.availability import CloudFeature, available_providers, credential_source
from app.cloud.providers import CloudProvider
from app.storage.cloud_credentials import _gcp_secure_replica_bucket_name
from app.storage.secure_vault import resolve_secure_storage
from app.utils.config import settings


def _platform_storage_regions(username: str, csp: str) -> List[Dict[str, Any]] | None:
    """Multi-region catalog entries for platform mode (None when BYOC or single region)."""
    resolvers = {
        "AWS": resolve_aws_credentials,
        "GCP": resolve_gcp_credentials,
        "Azure": resolve_azure_credentials,
    }
    resolve = resolvers.get(csp)
    if not resolve or resolve(username).get("is_byoc"):
        return None
    if not catalog_is_multi_region():
        return None
    regions: List[Dict[str, Any]] = []
    for bucket in get_platform_buckets_for_csp(csp):
        regions.append(
            {
                "slug": bucket.get("platform_slug"),
                "label": bucket.get("platform_label"),
                "bucket": bucket.get("name"),
                "region": bucket.get("region") or bucket.get("location") or "—",
            }
        )
    return regions or None


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
    payload = {
        "csp": "AWS",
        "credential_source": src,
        "storage": storage,
        "security": security,
    }
    regions = _platform_storage_regions(username, "AWS")
    if regions:
        payload["storage_regions"] = regions
    return payload


def _gcp_targets(username: str) -> Dict[str, Any]:
    gcp = resolve_gcp_credentials(username)
    layout = get_gcp_bucket_layout(username)
    bucket = gcp.get("bucket_name") or settings.GCP_BUCKET_NAME
    try:
        secure = resolve_secure_storage(username, "GCP")
        secure_bucket = secure.bucket_name
        secure_prefix = secure.object_key(username, "").rstrip("/") + "/"
    except Exception:
        secure_bucket = bucket
        secure_prefix = f"secure/{username}/"
    if layout:
        bucket = layout["storage_bucket_name"]
        secure_bucket = layout["secure_bucket_name"]
        secure_prefix = (
            f"{username}/"
            if layout.get("uses_dedicated_secure_bucket")
            else f"secure/{username}/"
        )
        replica_bucket = layout.get("replica_bucket_name") or None
        replica_region = layout.get("replica_location") or None
        primary_region = layout.get("primary_location") or "—"
        dual_write = layout.get("secure_dual_write", False)
    else:
        replica_bucket = _gcp_secure_replica_bucket_name() or None
        replica_region = None
        primary_region = settings.GCP_ZONE or "—"
        dual_write = bool(_gcp_secure_replica_bucket_name())
    payload = {
        "csp": "GCP",
        "credential_source": credential_source(username, "GCP"),
        "storage": {
            "bucket": bucket,
            "region": primary_region,
            "key_prefix": f"{username}/",
        },
        "security": {
            "bucket": secure_bucket,
            "region": primary_region,
            "key_prefix": secure_prefix,
            "replica_bucket": replica_bucket,
            "replica_region": replica_region,
            "secure_dual_write": dual_write,
        },
    }
    regions = _platform_storage_regions(username, "GCP")
    if regions:
        payload["storage_regions"] = regions
    return payload


def _azure_targets(username: str) -> Dict[str, Any]:
    az = resolve_azure_credentials(username)
    layout = get_azure_container_layout(username)
    container = az.get("container_name") or settings.AZURE_CONTAINER_NAME
    account = az.get("account_name") or settings.AZURE_STORAGE_ACCOUNT_NAME
    try:
        secure = resolve_secure_storage(username, "Azure")
        secure_container = secure.container_name
        secure_prefix = secure.object_key(username, "").rstrip("/") + "/"
    except Exception:
        secure_container = container
        secure_prefix = f"secure/{username}/"
    if layout:
        container = layout["storage_container_name"]
        secure_container = layout["secure_container_name"]
        secure_prefix = (
            f"{username}/"
            if layout.get("uses_dedicated_secure_container")
            else f"secure/{username}/"
        )
        replica_container = layout.get("replica_container_name") or None
        dual_write = layout.get("secure_dual_write", False)
    else:
        replica_container = (settings.AZURE_SECURE_REPLICA_CONTAINER_NAME or "").strip() or None
        dual_write = bool(replica_container)
    payload = {
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
            "region": settings.AZURE_LOCATION or "—",
            "key_prefix": secure_prefix,
            "replica_bucket": replica_container,
            "replica_region": None,
            "secure_dual_write": dual_write,
        },
    }
    regions = _platform_storage_regions(username, "Azure")
    if regions:
        payload["storage_regions"] = regions
    return payload


def build_storage_targets_payload(username: str) -> Dict[str, Any]:
    """Multi-cloud destinations for Storage / Security banners."""
    providers: List[CloudProvider] = available_providers(username, CloudFeature.STORAGE)
    by_csp: Dict[str, Any] = {}
    for p in providers:
        if p == "AWS":
            by_csp[p] = _aws_targets(username)
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
