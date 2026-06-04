"""Discover S3 buckets in a BYOC AWS account and classify them for Storage vs Security."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Set

import boto3
from botocore.exceptions import ClientError

from app.byoc.aws_bucket_helpers import (
    S3_CONFIG,
    SUPPORTED_AWS_REGIONS,
    normalize_s3_location_constraint,
)
from app.byoc.credential_resolver import (
    get_aws_bucket_layout,
    resolve_aws_credentials,
)
from app.database.mongo_client import get_database
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

CACHE_TTL_SECONDS = 600
CACHE_COLLECTION = "aws_bucket_cache"

Surface = Literal["storage", "security"]


def _cache_collection():
    return get_database()[CACHE_COLLECTION]


def infer_security_bucket_by_name(bucket_name: str) -> bool:
    """
    Heuristic for Zenith / vault-style bucket names not yet in BYOC layout.
    Keeps secure vault buckets off the Storage dashboard.
    """
    lower = bucket_name.lower().strip()
    if not lower:
        return False
    if lower.endswith("-replica") or lower.endswith("-secure"):
        return True
    if "zenith-" in lower and ("-secure" in lower or "-replica" in lower):
        return True
    if lower.endswith("-secure-vault") or lower.endswith("-securevault"):
        return True
    return False


def configured_security_bucket_names(layout: Optional[Dict[str, Any]]) -> Set[str]:
    """BYOC secure + replica bucket names (always Security-only in the UI)."""
    names: Set[str] = set()
    if not layout:
        return names
    for key in ("secure_bucket_name", "replica_bucket_name"):
        value = (layout.get(key) or "").strip()
        if value:
            names.add(value)
    return names


def classify_bucket_role(
    bucket_name: str,
    layout: Optional[Dict[str, Any]],
) -> str:
    """Return role: storage | secure | replica | other."""
    storage = (layout.get("storage_bucket_name") or "").strip() if layout else ""
    secure = (layout.get("secure_bucket_name") or "").strip() if layout else ""
    replica = (layout.get("replica_bucket_name") or "").strip() if layout else ""

    if replica and bucket_name == replica:
        return "replica"
    if secure and bucket_name == secure:
        return "secure"
    if storage and bucket_name == storage:
        # Shared bucket used for both general + secure prefixes → vault surface only
        if secure and storage == secure:
            return "secure"
        return "storage"
    if infer_security_bucket_by_name(bucket_name):
        if bucket_name.lower().endswith("-replica") or (
            "zenith-" in bucket_name.lower() and "-replica" in bucket_name.lower()
        ):
            return "replica"
        return "secure"
    return "other"


def is_security_bucket(role: str) -> bool:
    return role in ("secure", "replica")


def list_account_buckets_from_aws(
    access_key_id: str,
    secret_access_key: str,
    session_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List all buckets in the account with region and role hints.
    Requires s3:ListAllMyBuckets and s3:GetBucketLocation.
    """
    client_kwargs: dict = {
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
        "region_name": "us-east-1",
        "config": S3_CONFIG,
    }
    if session_token:
        client_kwargs["aws_session_token"] = session_token
    client = boto3.client("s3", **client_kwargs)

    try:
        resp = client.list_buckets()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        raise PermissionError(
            f"Cannot list buckets ({code}). Add s3:ListAllMyBuckets to your IAM policy."
        ) from e

    buckets: List[Dict[str, Any]] = []
    for entry in resp.get("Buckets", []) or []:
        name = entry.get("Name", "")
        if not name:
            continue
        region = "us-east-1"
        try:
            loc = client.get_bucket_location(Bucket=name).get("LocationConstraint")
            region = normalize_s3_location_constraint(loc)
        except ClientError:
            logger.warning("Could not resolve region for bucket %s", name)
        buckets.append({"name": name, "region": region})

    return buckets


def _enrich_buckets(
    raw: List[Dict[str, Any]],
    layout: Optional[Dict[str, Any]],
    default_storage: str,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for b in raw:
        name = b["name"]
        role = classify_bucket_role(name, layout)
        out.append(
            {
                "name": name,
                "region": b["region"],
                "role": role,
                "is_default": name == default_storage and role == "storage",
                "is_replica": role == "replica",
            }
        )
    return out


def _get_secure_bucket_names_from_db(username: str) -> Set[str]:
    db = get_database()
    names: Set[str] = set()
    for doc in db["secure_files"].find(
        {"owner_username": username, "cloud_bucket": {"$exists": True, "$ne": ""}},
        {"cloud_bucket": 1},
    ):
        cb = (doc.get("cloud_bucket") or "").strip()
        if cb:
            names.add(cb)
    return names


def _security_bucket_name_set(
    buckets: List[Dict[str, Any]],
    layout: Optional[Dict[str, Any]],
    extra_secure_names: Optional[Set[str]] = None,
) -> Set[str]:
    """All bucket names that belong on the Security page only."""
    names: Set[str] = set(extra_secure_names or set())
    names |= configured_security_bucket_names(layout)
    for b in buckets:
        if is_security_bucket(b.get("role", "")):
            names.add(b["name"])
        elif infer_security_bucket_by_name(b["name"]):
            names.add(b["name"])
    return names


def filter_buckets_for_surface(
    buckets: List[Dict[str, Any]],
    surface: Surface,
    extra_secure_names: Optional[Set[str]] = None,
    layout: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Storage = general buckets only; Security = vault (secure + replica) only."""
    security_names = _security_bucket_name_set(buckets, layout, extra_secure_names)

    if surface == "security":
        seen: Set[str] = set()
        result: List[Dict[str, Any]] = []
        for b in buckets:
            if b["name"] in security_names and b["name"] not in seen:
                result.append(b)
                seen.add(b["name"])
        for name in security_names:
            if name not in seen:
                result.append(
                    {
                        "name": name,
                        "region": "",
                        "role": "replica"
                        if layout
                        and name == (layout.get("replica_bucket_name") or "").strip()
                        else "secure",
                        "is_default": bool(
                            layout
                            and name == (layout.get("secure_bucket_name") or "").strip()
                        ),
                        "is_replica": bool(
                            layout
                            and name == (layout.get("replica_bucket_name") or "").strip()
                        ),
                    }
                )
        return sorted(result, key=lambda x: (x.get("is_replica", False), x["name"]))

    storage_only = [b for b in buckets if b["name"] not in security_names]
    result = [
        b
        for b in storage_only
        if not is_security_bucket(b.get("role", ""))
        and not infer_security_bucket_by_name(b["name"])
    ]
    if not result and layout and surface == "storage":
        storage_name = (layout.get("storage_bucket_name") or "").strip()
        if storage_name and storage_name not in security_names:
            result.append(
                {
                    "name": storage_name,
                    "region": (layout.get("primary_region") or "").strip(),
                    "role": "storage",
                    "is_default": True,
                    "is_replica": False,
                }
            )
    return result


def filter_by_region(
    buckets: List[Dict[str, Any]],
    region: Optional[str],
) -> List[Dict[str, Any]]:
    if not region or region.lower() in ("all", ""):
        return buckets
    return [b for b in buckets if b.get("region") == region]


def get_cached_raw_buckets(username: str) -> Optional[List[Dict[str, Any]]]:
    doc = _cache_collection().find_one({"username": username})
    if not doc:
        return None
    fetched_at = doc.get("fetched_at")
    if not fetched_at:
        return None
    if datetime.utcnow() - fetched_at > timedelta(seconds=CACHE_TTL_SECONDS):
        return None
    return doc.get("buckets")


def set_cached_raw_buckets(username: str, buckets: List[Dict[str, Any]]) -> None:
    _cache_collection().update_one(
        {"username": username},
        {"$set": {"buckets": buckets, "fetched_at": datetime.utcnow()}},
        upsert=True,
    )


def invalidate_bucket_cache(username: str) -> None:
    _cache_collection().delete_one({"username": username})


def fetch_and_cache_buckets(username: str, force: bool = False) -> List[Dict[str, Any]]:
    if not force:
        cached = get_cached_raw_buckets(username)
        if cached is not None:
            return cached

    aws = resolve_aws_credentials(username)
    if not aws.get("is_byoc"):
        return []

    raw = list_account_buckets_from_aws(
        aws["access_key_id"],
        aws["secret_access_key"],
        aws.get("session_token"),
    )
    set_cached_raw_buckets(username, raw)
    return raw


def platform_bucket_entries(surface: Surface, username: str) -> List[Dict[str, Any]]:
    """Static buckets for non-BYOC users."""
    regular = getattr(settings, "REGULAR_S3_BUCKET_NAME", settings.S3_BUCKET_NAME)
    secure = settings.SECURE_S3_BUCKET_NAME
    replica = settings.REPLICA_S3_BUCKET_NAME
    primary_region = settings.PRIMARY_S3_REGION
    replica_region = settings.REPLICA_S3_REGION

    if surface == "security":
        entries = [
            {
                "name": secure,
                "region": primary_region,
                "role": "secure",
                "is_default": True,
                "is_replica": False,
            },
            {
                "name": replica,
                "region": replica_region,
                "role": "replica",
                "is_default": False,
                "is_replica": True,
            },
        ]
        return entries

    return [
        {
            "name": regular,
            "region": primary_region,
            "role": "storage",
            "is_default": True,
            "is_replica": False,
        }
    ]


def get_buckets_for_user(
    username: str,
    surface: Surface,
    region: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Return { mode, buckets, discovery_error? } for Storage or Security UI.
    """
    aws = resolve_aws_credentials(username)
    layout = get_aws_bucket_layout(username)
    default_storage = (
        (layout or {}).get("storage_bucket_name")
        or aws.get("bucket_name")
        or getattr(settings, "REGULAR_S3_BUCKET_NAME", settings.S3_BUCKET_NAME)
    )

    if not aws.get("is_byoc"):
        buckets = platform_bucket_entries(surface, username)
        # Platform has fixed bucket(s) in PRIMARY_S3_REGION — ignore stale session
        # region filters (no region pills in UI for platform mode).
        filtered = filter_by_region(buckets, region)
        if not filtered and buckets:
            filtered = buckets
        return {
            "mode": "platform",
            "buckets": filtered,
            "supported_regions": [],
        }

    discovery_error: Optional[str] = None
    raw: List[Dict[str, Any]] = []
    try:
        raw = fetch_and_cache_buckets(username, force=force_refresh)
    except PermissionError as e:
        discovery_error = str(e)
        raw = []
    except Exception as e:
        discovery_error = f"Bucket discovery failed: {str(e)[:160]}"
        raw = []

    if not raw and layout:
        # Fallback to configured BYOC buckets when ListBuckets is denied
        fallback: List[Dict[str, Any]] = []
        for name, reg, role in [
            (layout.get("storage_bucket_name"), layout.get("primary_region"), "storage"),
            (layout.get("secure_bucket_name"), layout.get("primary_region"), "secure"),
            (layout.get("replica_bucket_name"), layout.get("replica_region"), "replica"),
        ]:
            if name:
                fallback.append({"name": name, "region": reg or aws.get("region", "")})
        raw = fallback

    enriched = _enrich_buckets(raw, layout, default_storage)
    extra_secure = _get_secure_bucket_names_from_db(username)
    filtered = filter_buckets_for_surface(enriched, surface, extra_secure, layout)
    region_filtered = filter_by_region(filtered, region)
    if not region_filtered and filtered and region:
        discovery_error = (
            discovery_error
            or f"No buckets in region {region}. Clear the region filter or choose All."
        )
    filtered = region_filtered if region_filtered or not region else filtered

    return {
        "mode": "byoc",
        "buckets": filtered,
        "supported_regions": list(SUPPORTED_AWS_REGIONS),
        "discovery_error": discovery_error,
    }
