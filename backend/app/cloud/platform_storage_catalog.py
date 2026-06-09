"""
Platform storage catalog — config-driven multi-region destinations (no cloud list APIs).

Regions are defined in PLATFORM_STORAGE_CATALOG (JSON string) or
PLATFORM_STORAGE_CATALOG_JSON (file path). Falls back to legacy single-bucket .env fields.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from app.utils.config import settings

Surface = Literal["storage", "security"]
Csp = Literal["AWS", "GCP", "Azure"]


def _catalog_path() -> Optional[Path]:
    raw = (getattr(settings, "PLATFORM_STORAGE_CATALOG_JSON", None) or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        backend_root = Path(__file__).resolve().parents[2]
        path = backend_root / raw
    return path if path.is_file() else None


def _load_catalog_raw() -> List[Dict[str, Any]]:
    inline = (getattr(settings, "PLATFORM_STORAGE_CATALOG", None) or "").strip()
    if inline:
        try:
            data = json.loads(inline)
            return data if isinstance(data, list) else data.get("regions", [])
        except json.JSONDecodeError:
            return []

    path = _catalog_path()
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else data.get("regions", [])
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _legacy_single_region() -> List[Dict[str, Any]]:
    """Single-bucket fallback from existing .env fields."""
    aws_bucket = (
        getattr(settings, "REGULAR_S3_BUCKET_NAME", None) or settings.S3_BUCKET_NAME
    )
    aws_region = settings.PRIMARY_S3_REGION
    return [
        {
            "slug": "asia",
            "label": "Asia",
            "aws": {"bucket": aws_bucket, "region": aws_region},
            "gcp": {
                "bucket": settings.GCP_BUCKET_NAME,
                "location": getattr(settings, "GCP_ZONE", "us-central1-a").split("-")[0].upper()
                if "-" in getattr(settings, "GCP_ZONE", "")
                else "ASIA-SOUTH1",
            },
            "azure": {
                "account_name": settings.AZURE_STORAGE_ACCOUNT_NAME,
                "account_key": settings.AZURE_STORAGE_ACCOUNT_KEY,
                "container": settings.AZURE_CONTAINER_NAME,
                "region": settings.AZURE_LOCATION,
            },
        }
    ]


@lru_cache(maxsize=1)
def get_platform_regions() -> List[Dict[str, Any]]:
    """All configured platform region entries (cached per process)."""
    regions = _load_catalog_raw()
    if not regions:
        regions = _legacy_single_region()
    return [r for r in regions if r.get("slug")]


def catalog_is_multi_region() -> bool:
    return len(get_platform_regions()) > 1


def default_platform_slug() -> str:
    regions = get_platform_regions()
    if not regions:
        return "asia"
    default = (getattr(settings, "PLATFORM_STORAGE_DEFAULT_SLUG", None) or "").strip()
    if default and any(r.get("slug") == default for r in regions):
        return default
    return str(regions[0].get("slug", "asia"))


def get_region_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    key = (slug or "").strip().lower()
    for region in get_platform_regions():
        if str(region.get("slug", "")).lower() == key:
            return region
    return None


def resolve_platform_destination_by_bucket(
    csp: str,
    bucket_or_container: str,
    *,
    cloud_region: Optional[str] = None,
    account_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find platform destination when bucket/container is known (sync/delete/download)."""
    name = (bucket_or_container or "").strip()
    if not name:
        return None
    csp_u = (csp or "").strip().upper()

    if csp_u == "AZURE":
        matches: List[Dict[str, Any]] = []
        for entry in get_platform_regions():
            az = entry.get("azure") or {}
            if az.get("container") == name:
                matches.append(entry)
        if not matches:
            return None
        if account_name:
            acct = account_name.strip().lower()
            for entry in matches:
                az = entry.get("azure") or {}
                if (az.get("account_name") or "").strip().lower() == acct:
                    return resolve_platform_destination("Azure", entry.get("slug"))
        if cloud_region:
            reg = cloud_region.strip().lower()
            for entry in matches:
                az = entry.get("azure") or {}
                if (az.get("region") or "").strip().lower() == reg:
                    return resolve_platform_destination("Azure", entry.get("slug"))
        return resolve_platform_destination("Azure", matches[0].get("slug"))

    for entry in get_platform_regions():
        if csp_u == "AWS":
            aws = entry.get("aws") or {}
            if aws.get("bucket") == name:
                if cloud_region and (aws.get("region") or "").strip().lower() != cloud_region.strip().lower():
                    continue
                return resolve_platform_destination("AWS", entry.get("slug"))
        elif csp_u == "GCP":
            gcp = entry.get("gcp") or {}
            if gcp.get("bucket") == name:
                if cloud_region:
                    loc = (gcp.get("location") or "").strip().lower()
                    if loc and loc != cloud_region.strip().lower():
                        continue
                return resolve_platform_destination("GCP", entry.get("slug"))
    return None


def get_region_by_aws_code(aws_region: str) -> Optional[Dict[str, Any]]:
    code = (aws_region or "").strip()
    for region in get_platform_regions():
        aws = region.get("aws") or {}
        if aws.get("region") == code:
            return region
    return None


def supported_aws_region_codes() -> List[str]:
    codes: List[str] = []
    for region in get_platform_regions():
        aws = region.get("aws") or {}
        code = (aws.get("region") or "").strip()
        if code and code not in codes:
            codes.append(code)
    return codes


def resolve_platform_destination(
    csp: str,
    region_slug: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Resolve upload/sync target for platform mode.
    Returns dict with bucket/container, region/location, and azure account fields.
    """
    csp_u = (csp or "").strip().upper()
    slug = (region_slug or default_platform_slug()).strip().lower()
    entry = get_region_by_slug(slug)
    if not entry:
        entry = get_platform_regions()[0] if get_platform_regions() else None
    if not entry:
        return None

    if csp_u == "AWS":
        aws = entry.get("aws") or {}
        bucket = (aws.get("bucket") or "").strip()
        if not bucket:
            return None
        return {
            "csp": "AWS",
            "platform_slug": entry.get("slug"),
            "bucket": bucket,
            "region": aws.get("region") or settings.PRIMARY_S3_REGION,
            "label": entry.get("label"),
        }

    if csp_u == "GCP":
        gcp = entry.get("gcp") or {}
        bucket = (gcp.get("bucket") or "").strip()
        if not bucket:
            return None
        return {
            "csp": "GCP",
            "platform_slug": entry.get("slug"),
            "bucket": bucket,
            "location": gcp.get("location") or "",
            "region": gcp.get("location") or "",
            "label": entry.get("label"),
        }

    if csp_u == "AZURE":
        az = entry.get("azure") or {}
        container = (az.get("container") or "").strip()
        account = (az.get("account_name") or "").strip()
        key = (az.get("account_key") or "").strip()
        if not container or not account or not key:
            return None
        return {
            "csp": "Azure",
            "platform_slug": entry.get("slug"),
            "bucket": container,
            "container": container,
            "account_name": account,
            "account_key": key,
            "region": az.get("region") or settings.AZURE_LOCATION,
            "label": entry.get("label"),
        }

    return None


def get_platform_buckets_for_csp(
    csp: str,
    *,
    surface: Surface = "storage",
) -> List[Dict[str, Any]]:
    """Bucket/container list for Storage UI (platform mode, zero cloud APIs)."""
    if surface != "storage":
        return _legacy_security_buckets_for_csp(csp)

    csp_u = (csp or "").strip().upper()
    default_slug = default_platform_slug()
    out: List[Dict[str, Any]] = []

    for entry in get_platform_regions():
        slug = entry.get("slug", "")
        label = entry.get("label", slug)
        is_default = slug == default_slug

        if csp_u == "AWS":
            aws = entry.get("aws") or {}
            name = (aws.get("bucket") or "").strip()
            if not name:
                continue
            out.append(
                {
                    "name": name,
                    "region": aws.get("region") or "",
                    "role": "storage",
                    "is_default": is_default,
                    "is_replica": False,
                    "platform_slug": slug,
                    "platform_label": label,
                }
            )
        elif csp_u == "GCP":
            gcp = entry.get("gcp") or {}
            name = (gcp.get("bucket") or "").strip()
            if not name:
                continue
            out.append(
                {
                    "name": name,
                    "location": gcp.get("location") or "",
                    "region": gcp.get("location") or "",
                    "is_default": is_default,
                    "platform_slug": slug,
                    "platform_label": label,
                }
            )
        elif csp_u == "AZURE":
            az = entry.get("azure") or {}
            name = (az.get("container") or "").strip()
            if not name:
                continue
            out.append(
                {
                    "name": name,
                    "account_name": az.get("account_name") or "",
                    "region": az.get("region") or "",
                    "is_default": is_default,
                    "platform_slug": slug,
                    "platform_label": label,
                }
            )

    return out


def _legacy_security_buckets_for_csp(csp: str) -> List[Dict[str, Any]]:
    """Security surface still uses dedicated secure/replica buckets from .env."""
    csp_u = (csp or "").strip().upper()
    if csp_u == "AWS":
        return [
            {
                "name": settings.SECURE_S3_BUCKET_NAME,
                "region": settings.PRIMARY_S3_REGION,
                "role": "secure",
                "is_default": True,
                "is_replica": False,
            },
            {
                "name": settings.REPLICA_S3_BUCKET_NAME,
                "region": settings.REPLICA_S3_REGION,
                "role": "replica",
                "is_default": False,
                "is_replica": True,
            },
        ]
    dest = resolve_platform_destination(csp_u, default_platform_slug())
    if not dest:
        return []
    return [
        {
            "name": dest.get("bucket") or dest.get("container") or "",
            "region": dest.get("region") or "",
            "role": "storage",
            "is_default": True,
            "is_replica": False,
            "platform_slug": dest.get("platform_slug"),
        }
    ]


def invalidate_platform_catalog_cache() -> None:
    get_platform_regions.cache_clear()
