"""BYOC layout normalization for legacy and three-bucket records."""

from app.byoc.credential_resolver import normalize_aws_byoc_layout


def test_normalize_legacy_single_bucket():
    layout = normalize_aws_byoc_layout(
        {"bucket_name": "old-bucket", "primary_region": "ap-south-1"}
    )
    assert layout["storage_bucket_name"] == "old-bucket"
    assert layout["secure_bucket_name"] == "old-bucket"
    assert layout["replica_bucket_name"] == ""
    assert layout["secure_dual_write"] is False
    assert layout["uses_dedicated_secure_bucket"] is False


def test_normalize_three_bucket_dual_write():
    layout = normalize_aws_byoc_layout(
        {
            "storage_bucket_name": "s-bucket",
            "secure_bucket_name": "sec-bucket",
            "replica_bucket_name": "rep-bucket",
            "primary_region": "ap-south-1",
            "replica_region": "us-east-1",
            "secure_dual_write": True,
        }
    )
    assert layout["secure_dual_write"] is True
    assert layout["uses_dedicated_secure_bucket"] is True
    assert layout["replica_bucket_name"] == "rep-bucket"
