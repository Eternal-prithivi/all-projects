"""Secure vault dual-write helpers (BYOC three-bucket layout)."""

from unittest.mock import MagicMock, patch

from app.storage.cloud_credentials import (
    SecureAwsStorage,
    put_secure_object_dual,
)


def test_put_secure_object_dual_writes_replica():
    primary = MagicMock()
    replica = MagicMock()
    storage = SecureAwsStorage(
        primary_client=primary,
        replica_client=replica,
        primary_bucket="sec-primary",
        replica_bucket="sec-replica",
        region="ap-south-1",
        is_byoc=True,
        list_prefix="alice/",
        access_key_id="AKIA",
        secret_access_key="secret",
        dedicated_secure_bucket=True,
    )
    put_secure_object_dual(
        storage, "alice/doc.pdf", b"data", server_side_encryption=True
    )
    primary.put_object.assert_called_once()
    replica.put_object.assert_called_once()


def test_put_secure_object_dual_skips_replica_when_disabled():
    primary = MagicMock()
    replica = MagicMock()
    storage = SecureAwsStorage(
        primary_client=primary,
        replica_client=replica,
        primary_bucket="sec-primary",
        replica_bucket="sec-replica",
        region="ap-south-1",
        is_byoc=True,
        list_prefix="alice/",
        access_key_id="AKIA",
        secret_access_key="secret",
        dedicated_secure_bucket=True,
    )
    put_secure_object_dual(
        storage, "alice/doc.pdf", b"data", server_side_encryption=True, replicate=False
    )
    assert primary.put_object.call_count == 1
    replica.put_object.assert_not_called()


@patch("app.storage.cloud_credentials.get_aws_bucket_layout")
@patch("app.storage.cloud_credentials.resolve_aws_credentials")
def test_resolve_secure_byoc_enables_replica_client(mock_resolve, mock_layout):
    mock_resolve.return_value = {
        "access_key_id": "AKIA",
        "secret_access_key": "secret",
        "session_token": "tok",
        "bucket_name": "storage-b",
        "region": "ap-south-1",
        "is_byoc": True,
    }
    mock_layout.return_value = {
        "storage_bucket_name": "storage-b",
        "secure_bucket_name": "secure-b",
        "replica_bucket_name": "replica-b",
        "primary_region": "ap-south-1",
        "replica_region": "us-east-1",
        "secure_dual_write": True,
        "uses_dedicated_secure_bucket": True,
    }
    with patch("app.storage.cloud_credentials.boto3.client") as mock_boto:
        mock_boto.return_value = MagicMock()
        from app.storage.cloud_credentials import resolve_secure_aws_storage

        storage = resolve_secure_aws_storage("alice")
    assert storage.primary_bucket == "secure-b"
    assert storage.replica_bucket == "replica-b"
    assert storage.dual_write_enabled is True
    assert storage.list_prefix == "alice/"
    assert mock_boto.call_count == 2
