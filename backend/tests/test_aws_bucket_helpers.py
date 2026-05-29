"""Unit tests for AWS BYOC bucket naming helpers (no live AWS calls)."""

from app.byoc.aws_bucket_helpers import (
    suggest_aws_bucket_names,
    sanitize_username_for_bucket,
    validate_bucket_name_format,
)


def test_suggest_aws_bucket_names_unique_suffix():
    names = suggest_aws_bucket_names("alice")
    assert names["storage_bucket_name"].startswith("zenith-alice-")
    assert names["storage_bucket_name"].endswith("-storage")
    assert names["secure_bucket_name"].endswith("-secure")
    assert names["replica_bucket_name"].endswith("-replica")
    second = suggest_aws_bucket_names("alice")
    assert second["storage_bucket_name"] != names["storage_bucket_name"]


def test_sanitize_username_for_bucket():
    assert sanitize_username_for_bucket("User.Name!") == "user-name"


def test_validate_bucket_name_format_ok():
    assert validate_bucket_name_format("zenith-alice-abc123-storage") is None


def test_validate_bucket_name_format_rejects_uppercase():
    assert validate_bucket_name_format("MyBucket") is not None
