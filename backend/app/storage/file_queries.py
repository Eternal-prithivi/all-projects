"""MongoDB helpers for multi-bucket file lookups."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pymongo.collection import Collection


def build_platform_region_list_filter(
    username: str,
    platform_slug: str,
) -> Dict[str, Any]:
    """Match file rows for one platform region pill (all CSPs)."""
    from app.cloud.platform_storage_catalog import resolve_platform_destination

    slug = (platform_slug or "").strip().lower()
    or_clauses: List[Dict[str, Any]] = [{"platform_slug": slug}]
    for csp in ("AWS", "GCP", "Azure"):
        dest = resolve_platform_destination(csp, slug)
        if not dest:
            continue
        bucket = (dest.get("bucket") or dest.get("container") or "").strip()
        region = (dest.get("region") or dest.get("location") or "").strip()
        account = (dest.get("account_name") or "").strip()
        if not bucket:
            continue
        leg: Dict[str, Any] = {"csp": csp, "cloud_bucket": bucket}
        if csp == "Azure" and account:
            leg["cloud_account"] = account
        elif region:
            leg["region"] = region
        or_clauses.append(leg)
    return {"owner_username": username, "$or": or_clauses}


def build_storage_list_filter(
    username: str,
    bucket: Optional[str],
    region: Optional[str],
    default_bucket: str,
) -> Dict[str, Any]:
    """Filter files for list endpoint."""
    clauses: List[Dict[str, Any]] = [{"owner_username": username}]
    if bucket:
        if bucket == default_bucket:
            clauses.append(
                {
                    "$or": [
                        {"cloud_bucket": bucket},
                        {"cloud_bucket": {"$exists": False}},
                        {"cloud_bucket": None},
                        {"cloud_bucket": ""},
                    ]
                }
            )
        else:
            clauses.append({"cloud_bucket": bucket})
    if region:
        clauses.append(
            {
                "$or": [
                    {"region": region},
                    {"region": {"$exists": False}},
                    {"region": None},
                    {"region": ""},
                ]
            }
        )
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def build_secure_list_filter(
    username: str,
    bucket: Optional[str],
    region: Optional[str],
    default_bucket: str,
) -> Dict[str, Any]:
    return build_storage_list_filter(username, bucket, region, default_bucket)


def find_storage_file(
    files_db: Collection,
    username: str,
    filename: str,
    bucket: Optional[str] = None,
    region: Optional[str] = None,
    platform_slug: Optional[str] = None,
    cloud_account: Optional[str] = None,
) -> Dict[str, Any]:
    base: Dict[str, Any] = {"owner_username": username, "filename": filename}
    disambiguators: Dict[str, Any] = {}
    if bucket:
        disambiguators["cloud_bucket"] = bucket
    if platform_slug:
        disambiguators["platform_slug"] = platform_slug
    if cloud_account:
        disambiguators["cloud_account"] = cloud_account
    if region:
        disambiguators["region"] = region

    if disambiguators:
        matches = list(files_db.find({**base, **disambiguators}))
        if matches:
            if len(matches) > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Multiple files match. Specify region or platform_slug.",
                )
            return matches[0]

    matches = list(files_db.find(base))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found in database.")
    if len(matches) == 1:
        return matches[0]
    if bucket:
        bucket_matches = [m for m in matches if m.get("cloud_bucket") == bucket]
        if len(bucket_matches) == 1:
            return bucket_matches[0]
    if region:
        region_matches = [
            m for m in matches if (m.get("region") or "").lower() == region.lower()
        ]
        if len(region_matches) == 1:
            return region_matches[0]
    raise HTTPException(
        status_code=400,
        detail="Multiple files share this name. Specify bucket and region query parameters.",
    )


def find_secure_file(
    files_db: Collection,
    username: str,
    filename: str,
    bucket: Optional[str] = None,
) -> Dict[str, Any]:
    return find_storage_file(files_db, username, filename, bucket)
