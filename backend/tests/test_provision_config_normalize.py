"""Provision config S3 bucket name normalization."""

import pytest

from app.provision.config_normalize import (
    normalize_provision_config,
    sanitize_s3_bucket_name,
)


def test_sanitize_bucket_strips_and_lowercases():
    assert sanitize_s3_bucket_name("My-testing-bucket-for-Zenith ") == "my-testing-bucket-for-zenith"


def test_normalize_provision_config_s3():
    config = {"enable_s3": True, "bucket_name": "My-Bucket Name"}
    normalize_provision_config(config)
    assert config["bucket_name"] == "my-bucket-name"


def test_normalize_rejects_empty_s3_name():
    config = {"enable_s3": True, "bucket_name": "  "}
    with pytest.raises(ValueError, match="required"):
        normalize_provision_config(config)
