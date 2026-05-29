"""MongoDB helpers for multi-bucket file lookups."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pymongo.collection import Collection


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
) -> Dict[str, Any]:
    query: Dict[str, Any] = {"owner_username": username, "filename": filename}
    if bucket:
        query["cloud_bucket"] = bucket
    matches = list(files_db.find(query))
    if not matches and bucket:
        raise HTTPException(status_code=404, detail="File not found in database.")
    if not matches:
        matches = list(files_db.find({"owner_username": username, "filename": filename}))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found in database.")
    if len(matches) > 1 and not bucket:
        raise HTTPException(
            status_code=400,
            detail="Multiple files share this name. Specify the bucket query parameter.",
        )
    return matches[0]


def find_secure_file(
    files_db: Collection,
    username: str,
    filename: str,
    bucket: Optional[str] = None,
) -> Dict[str, Any]:
    return find_storage_file(files_db, username, filename, bucket)
