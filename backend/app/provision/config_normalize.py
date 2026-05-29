"""Normalize and validate provision wizard config before Terraform."""

from __future__ import annotations

import re
from typing import Any

from app.byoc.aws_bucket_helpers import validate_bucket_name_format

_S3_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


def sanitize_s3_bucket_name(name: str) -> str:
    """Lowercase, strip, and replace invalid chars (matches AWS S3 naming rules)."""
    if not name:
        return ""
    cleaned = name.strip().lower()
    cleaned = re.sub(r"[^a-z0-9.-]", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip(".-")
    return cleaned[:63]


def validate_provision_s3_bucket(name: str) -> str | None:
    """Return error message if invalid, else None."""
    if not name:
        return "S3 bucket name is required when S3 is enabled."
    return validate_bucket_name_format(name) or (
        None if _S3_BUCKET_RE.match(name) else "Invalid S3 bucket name."
    )


def normalize_provision_config(config: dict[str, Any]) -> None:
    """In-place normalization for resource names used in terraform.tfvars."""
    if config.get("enable_s3"):
        raw = config.get("bucket_name") or ""
        sanitized = sanitize_s3_bucket_name(str(raw))
        config["bucket_name"] = sanitized
        err = validate_provision_s3_bucket(sanitized)
        if err:
            raise ValueError(err)

    if config.get("enable_dynamodb"):
        table = sanitize_s3_bucket_name(str(config.get("dynamodb_table_name") or ""))
        config["dynamodb_table_name"] = table.replace(".", "-")

    role = str(config.get("role_name") or "app-role").strip()
    config["role_name"] = re.sub(r"[^a-zA-Z0-9+=,.@_-]", "-", role)[:64] or "app-role"
