"""Secure vault uses BYOC bucket with secure/ prefix when AWS BYOC is configured."""

from unittest.mock import MagicMock, patch

from app.storage.cloud_credentials import resolve_secure_aws_storage


@patch("app.storage.cloud_credentials.get_aws_bucket_layout")
@patch("app.storage.cloud_credentials.resolve_aws_credentials")
def test_resolve_secure_byoc_shared_bucket_uses_prefix(mock_resolve, mock_layout):
    mock_resolve.return_value = {
        "access_key_id": "AKIA",
        "secret_access_key": "secret",
        "bucket_name": "customer-bucket",
        "region": "us-east-1",
        "is_byoc": True,
    }
    mock_layout.return_value = {
        "storage_bucket_name": "customer-bucket",
        "secure_bucket_name": "customer-bucket",
        "replica_bucket_name": "",
        "primary_region": "us-east-1",
        "replica_region": "us-east-1",
        "secure_dual_write": False,
        "uses_dedicated_secure_bucket": False,
    }
    with patch("app.storage.cloud_credentials.boto3.client", return_value=MagicMock()):
        storage = resolve_secure_aws_storage("alice")
    assert storage.is_byoc is True
    assert storage.primary_bucket == "customer-bucket"
    assert storage.list_prefix == "secure/alice/"
    assert storage.object_key("alice", "report.pdf") == "secure/alice/report.pdf"
    assert storage.dual_write_enabled is False
