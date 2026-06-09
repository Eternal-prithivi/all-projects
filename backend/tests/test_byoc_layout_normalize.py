"""BYOC layout normalization for legacy and three-bucket records."""

from app.byoc.credential_resolver import (
    normalize_aws_byoc_layout,
    normalize_azure_byoc_layout,
    normalize_gcp_byoc_layout,
)


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


def test_normalize_gcp_three_bucket_dual_write():
    layout = normalize_gcp_byoc_layout(
        {
            "storage_bucket_name": "gcp-storage",
            "secure_bucket_name": "gcp-secure",
            "replica_bucket_name": "gcp-replica",
            "gcp_primary_location": "ASIA-SOUTH1",
            "gcp_replica_location": "US-EAST1",
            "secure_dual_write": True,
        }
    )
    assert layout["storage_bucket_name"] == "gcp-storage"
    assert layout["secure_bucket_name"] == "gcp-secure"
    assert layout["replica_bucket_name"] == "gcp-replica"
    assert layout["secure_dual_write"] is True
    assert layout["uses_dedicated_secure_bucket"] is True


def test_normalize_azure_three_container_dual_write():
    layout = normalize_azure_byoc_layout(
        {
            "storage_container_name": "az-storage",
            "secure_container_name": "az-secure",
            "replica_container_name": "az-replica",
            "secure_dual_write": True,
        }
    )
    assert layout["storage_container_name"] == "az-storage"
    assert layout["secure_container_name"] == "az-secure"
    assert layout["replica_container_name"] == "az-replica"
    assert layout["secure_dual_write"] is True
    assert layout["uses_dedicated_secure_container"] is True
