"""GCS bucket helpers for BYOC connect (suggest, validate, create)."""

from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional, Tuple

from app.byoc.aws_bucket_helpers import sanitize_username_for_bucket

GCP_PRIMARY_LOCATION_DEFAULT = "ASIA-SOUTH1"
GCP_REPLICA_LOCATION_DEFAULT = "US-EAST1"

GCS_BUCKET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$")


def suggest_gcp_bucket_names(username: str) -> Dict[str, str]:
    suffix = uuid.uuid4().hex[:6]
    base = sanitize_username_for_bucket(username)
    storage = f"zenith-{base}-{suffix}-storage"
    secure = f"zenith-{base}-{suffix}-secure"
    replica = f"zenith-{base}-{suffix}-replica"
    return {
        "storage_bucket_name": storage,
        "gcp_bucket_name": storage,
        "secure_bucket_name": secure,
        "replica_bucket_name": replica,
    }


def validate_gcp_bucket_name(name: str) -> Optional[str]:
    if not name or len(name) < 3 or len(name) > 63:
        return "Bucket name must be 3–63 characters."
    if not GCS_BUCKET_NAME_RE.match(name):
        return "Use lowercase letters, numbers, dots, hyphens, or underscores."
    if ".." in name or name.startswith(".") or name.endswith("."):
        return "Bucket name cannot start or end with a dot or contain '..'."
    return None


def _client_from_sa_json(service_account_json: str):
    from app.byoc.gcp_bucket_discovery import _client_from_sa_json

    return _client_from_sa_json(service_account_json)


def create_gcp_bucket(
    service_account_json: str,
    bucket_name: str,
    location: str,
) -> Tuple[bool, str]:
    """Create a GCS bucket if it does not exist."""
    try:
        client, _ = _client_from_sa_json(service_account_json)
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            return True, f"Bucket '{bucket_name}' already exists."
        client.create_bucket(bucket_name, location=location)
        return True, f"Created bucket '{bucket_name}' in {location}."
    except Exception as exc:
        return False, f"Could not create bucket '{bucket_name}': {str(exc)[:160]}"


def ensure_gcp_buckets_exist(
    service_account_json: str,
    buckets: List[Tuple[str, str]],
) -> Tuple[bool, str]:
    """Ensure each (name, location) bucket exists; create missing buckets."""
    created: List[str] = []
    for name, location in buckets:
        if not name:
            continue
        fmt = validate_gcp_bucket_name(name)
        if fmt:
            return False, fmt
        ok, message = create_gcp_bucket(service_account_json, name, location)
        if not ok:
            return False, message
        if message.startswith("Created"):
            created.append(name)
    if created:
        return True, f"Created bucket(s): {', '.join(created)}."
    return True, "All buckets already exist."
