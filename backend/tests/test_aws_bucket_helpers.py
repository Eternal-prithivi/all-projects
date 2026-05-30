"""Unit tests for AWS BYOC bucket naming helpers (no live AWS calls)."""

from unittest.mock import MagicMock, patch

from app.byoc.aws_bucket_helpers import (
    check_bucket_access,
    create_s3_bucket,
    resolve_bucket_target_region,
    suggest_aws_bucket_names,
    sanitize_username_for_bucket,
    validate_bucket_name_format,
    REPLICA_REGION_DEFAULT,
)


def test_resolve_bucket_target_region_replica_always_virginia():
    assert resolve_bucket_target_region("replica", "ap-south-1", "ap-south-1") == REPLICA_REGION_DEFAULT
    assert resolve_bucket_target_region("storage", None, "ap-south-1") == "ap-south-1"


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


@patch("app.byoc.aws_bucket_helpers.check_bucket_access")
@patch("app.byoc.aws_bucket_helpers._s3_client_from_keys")
def test_create_s3_bucket_skips_when_accessible(mock_client_factory, mock_check):
    mock_check.return_value = "accessible"
    ok, msg = create_s3_bucket("AKIA", "secret", "zenith-test-bucket", "ap-south-1")
    assert ok is True
    assert "already exists" in msg
    mock_client_factory.assert_not_called()


@patch("app.byoc.aws_bucket_helpers.get_bucket_actual_region", return_value="ap-south-1")
@patch("app.byoc.aws_bucket_helpers._apply_bucket_baseline")
@patch("app.byoc.aws_bucket_helpers.check_bucket_access")
@patch("app.byoc.aws_bucket_helpers._s3_client_from_keys")
def test_create_s3_bucket_creates_when_available(
    mock_client_factory, mock_check, mock_baseline, _mock_region
):
    # First call: name free; second call: post-create verification
    mock_check.side_effect = ["available", "accessible"]
    client = MagicMock()
    mock_client_factory.return_value = client
    ok, msg = create_s3_bucket("AKIA", "secret", "zenith-new-bucket", "ap-south-1")
    assert ok is True
    assert "created" in msg.lower()
    client.create_bucket.assert_called_once()
    mock_baseline.assert_called_once()
