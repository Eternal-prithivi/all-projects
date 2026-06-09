"""Secure vault archive moves objects to replica; restore copies back to primary."""

from unittest.mock import MagicMock, patch

import pytest

from app.storage.cloud_credentials import SecureAwsStorage
from app.storage.secure_vault import (
    SecureAzureStorage,
    SecureGcpStorage,
    SecureVaultArchiveError,
    archive_secure_vault_object,
    delete_secure_vault_object,
    restore_secure_vault_object,
)


def _aws_storage() -> SecureAwsStorage:
    return SecureAwsStorage(
        primary_client=MagicMock(),
        replica_client=MagicMock(),
        primary_bucket="zenith-secure-files",
        replica_bucket="zenith-secure-files-replica",
        region="ap-south-1",
        is_byoc=False,
        list_prefix="alice/",
        access_key_id="key",
        secret_access_key="secret",
    )


@patch("app.storage.secure_vault._aws_object_exists")
@patch("app.storage.secure_vault.copy_secure_object_to_replica")
def test_archive_aws_moves_primary_to_replica(mock_copy, mock_exists):
    mock_exists.side_effect = lambda client, bucket, key: bucket == "zenith-secure-files"
    storage = _aws_storage()

    replica = archive_secure_vault_object(storage, "alice/doc.pdf")

    assert replica == "zenith-secure-files-replica"
    mock_copy.assert_called_once()
    storage.primary_client.delete_object.assert_called_once_with(
        Bucket="zenith-secure-files", Key="alice/doc.pdf"
    )


@patch("app.storage.secure_vault._delete_replica_vault_object")
@patch("app.storage.secure_vault._aws_object_exists")
@patch("app.storage.secure_vault.copy_secure_object_from_replica")
def test_restore_aws_copies_replica_to_primary_and_deletes_replica(
    mock_copy, mock_exists, mock_delete_replica
):
    mock_exists.side_effect = lambda client, bucket, key: bucket == "zenith-secure-files-replica"
    storage = _aws_storage()

    primary = restore_secure_vault_object(storage, "alice/doc.pdf")

    assert primary == "zenith-secure-files"
    mock_copy.assert_called_once()
    mock_delete_replica.assert_called_once_with(storage, "alice/doc.pdf")


@patch("app.storage.secure_vault._aws_object_exists", return_value=False)
def test_archive_aws_missing_object_raises(_mock_exists):
    storage = _aws_storage()
    with pytest.raises(SecureVaultArchiveError):
        archive_secure_vault_object(storage, "alice/missing.pdf")


@patch("app.storage.secure_vault.delete_secure_object_dual")
def test_delete_aws_targets_primary_and_replica(mock_dual_delete):
    storage = _aws_storage()
    delete_secure_vault_object(storage, "alice/doc.pdf")
    mock_dual_delete.assert_called_once_with(storage, "alice/doc.pdf")


@patch("app.storage.secure_vault._delete_gcp_blob_if_exists")
def test_delete_gcp_targets_primary_and_replica(mock_gcp_delete):
    client = MagicMock()
    storage = SecureGcpStorage(
        client=client,
        bucket_name="zenith-secure-gcp",
        is_byoc=False,
        list_prefix="alice/",
        replica_bucket="zenith-secure-gcp-replica",
    )
    delete_secure_vault_object(storage, "alice/doc.pdf")
    assert mock_gcp_delete.call_count == 2
    mock_gcp_delete.assert_any_call(client, "zenith-secure-gcp", "alice/doc.pdf")
    mock_gcp_delete.assert_any_call(client, "zenith-secure-gcp-replica", "alice/doc.pdf")


@patch("app.storage.secure_vault._delete_azure_blob_if_exists")
def test_delete_azure_targets_primary_and_replica(mock_azure_delete):
    blob_service = MagicMock()
    storage = SecureAzureStorage(
        blob_service=blob_service,
        container_name="zenith-secure",
        is_byoc=False,
        list_prefix="alice/",
        replica_container="zenith-secure-replica",
    )
    delete_secure_vault_object(storage, "alice/doc.pdf")
    assert mock_azure_delete.call_count == 2
    mock_azure_delete.assert_any_call(blob_service, "zenith-secure", "alice/doc.pdf")
    mock_azure_delete.assert_any_call(blob_service, "zenith-secure-replica", "alice/doc.pdf")
