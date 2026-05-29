"""S3 helpers — per-user BYOC bucket or platform default."""

from typing import Any, Tuple

from app.storage.cloud_credentials import build_aws_s3_client, resolve_secure_aws_storage


def get_storage_client(username: str) -> Tuple[Any, str, bool]:
    return build_aws_s3_client(username)


def get_secure_storage(username: str):
    return resolve_secure_aws_storage(username)
