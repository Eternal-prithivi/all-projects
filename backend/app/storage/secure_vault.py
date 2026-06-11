"""Multi-cloud secure vault storage (AWS SSE dual-write, GCS, Azure Blob)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional, Union

from app.byoc.credential_resolver import (
    get_user_cloud_credentials,
    resolve_azure_credentials,
    resolve_gcp_credentials,
)
from app.cloud.providers import CloudProvider, normalize_provider
from app.storage.cloud_credentials import (
    SecureAwsStorage,
    _gcp_secure_replica_bucket_name,
    build_azure_secure_blob_service,
    build_gcp_secure_storage_client,
    copy_secure_object_from_replica,
    copy_secure_object_to_replica,
    delete_secure_object_dual,
    put_secure_object_dual,
    resolve_secure_aws_storage,
)


class SecureVaultArchiveError(Exception):
    """Archive/restore could not be completed in cloud storage."""

SecureVaultStorage = Union[SecureAwsStorage, "SecureGcpStorage", "SecureAzureStorage"]


@dataclass
class SecureGcpStorage:
    client: Any
    bucket_name: str
    is_byoc: bool
    list_prefix: str
    project_id: str = ""
    replica_bucket: Optional[str] = None

    def object_key(self, username: str, filename: str) -> str:
        return f"{self.list_prefix}{filename}"

    @property
    def primary_bucket(self) -> str:
        return self.bucket_name

    @property
    def region(self) -> str:
        return ""

    @property
    def dual_write_enabled(self) -> bool:
        return bool(self.replica_bucket)


@dataclass
class SecureAzureStorage:
    blob_service: Any
    container_name: str
    is_byoc: bool
    list_prefix: str
    replica_container: Optional[str] = None
    account_name: str = ""

    def object_key(self, username: str, filename: str) -> str:
        return f"{self.list_prefix}{filename}"

    @property
    def primary_bucket(self) -> str:
        return self.container_name

    @property
    def region(self) -> str:
        return ""

    @property
    def dual_write_enabled(self) -> bool:
        return bool(self.replica_container)


def resolve_secure_gcp_storage(username: str) -> SecureGcpStorage:
    client, bucket_name, is_byoc = build_gcp_secure_storage_client(username)
    storage_bucket = (resolve_gcp_credentials(username).get("bucket_name") or "").strip()
    dedicated = is_byoc and bucket_name != storage_bucket
    prefix = f"{username}/" if (not is_byoc or dedicated) else f"secure/{username}/"
    project_id = getattr(client, "project", None) or ""
    replica_bucket: Optional[str] = None
    if is_byoc:
        byoc = get_user_cloud_credentials(username, "GCP")
        if byoc:
            replica = (byoc.get("replica_bucket_name") or "").strip()
            if replica:
                replica_bucket = replica
    else:
        replica = _gcp_secure_replica_bucket_name()
        if replica:
            replica_bucket = replica
    return SecureGcpStorage(
        client=client,
        bucket_name=bucket_name,
        is_byoc=is_byoc,
        list_prefix=prefix,
        project_id=str(project_id or ""),
        replica_bucket=replica_bucket,
    )


def resolve_secure_azure_storage(username: str) -> SecureAzureStorage:
    from app.utils.config import settings

    blob_service, container_name, is_byoc, account_name, _key = (
        build_azure_secure_blob_service(username)
    )
    storage_container = (
        resolve_azure_credentials(username).get("container_name") or ""
    ).strip()
    dedicated = is_byoc and container_name != storage_container
    prefix = f"{username}/" if (not is_byoc or dedicated) else f"secure/{username}/"
    replica_container: Optional[str] = None
    if is_byoc:
        byoc = get_user_cloud_credentials(username, "Azure") or {}
        replica = (byoc.get("replica_container_name") or "").strip()
        if replica:
            replica_container = replica
    else:
        replica = (settings.AZURE_SECURE_REPLICA_CONTAINER_NAME or "").strip()
        if replica:
            replica_container = replica
    return SecureAzureStorage(
        blob_service=blob_service,
        container_name=container_name,
        is_byoc=is_byoc,
        list_prefix=prefix,
        replica_container=replica_container,
        account_name=account_name,
    )


def resolve_secure_storage(username: str, csp: str = "AWS") -> SecureVaultStorage:
    provider: CloudProvider = normalize_provider(csp)
    if provider == "GCP":
        return resolve_secure_gcp_storage(username)
    if provider == "Azure":
        return resolve_secure_azure_storage(username)
    return resolve_secure_aws_storage(username)


def secure_replication_requested(storage: SecureVaultStorage, enabled: bool) -> bool:
    """True when caller asked for replication and this vault supports a second copy."""
    if not enabled:
        return False
    if isinstance(storage, SecureAwsStorage):
        return True
    if isinstance(storage, SecureGcpStorage):
        return storage.dual_write_enabled
    if isinstance(storage, SecureAzureStorage):
        return storage.dual_write_enabled
    return False


def vault_csp(storage: SecureVaultStorage) -> str:
    if isinstance(storage, SecureAwsStorage):
        return "AWS"
    if isinstance(storage, SecureGcpStorage):
        return "GCP"
    return "Azure"


def platform_secure_primary_name(csp: str) -> str:
    """Configured primary secure vault bucket/container for platform mode."""
    from app.utils.config import settings

    csp_u = (csp or "").strip().upper()
    if csp_u == "GCP":
        return (settings.GCP_SECURE_BUCKET_NAME or "").strip()
    if csp_u == "AZURE":
        return (settings.AZURE_SECURE_CONTAINER_NAME or "").strip()
    return (settings.SECURE_S3_BUCKET_NAME or "").strip()


def platform_secure_replica_name(csp: str) -> str:
    """Configured replica secure vault bucket/container (platform mode)."""
    from app.storage.cloud_credentials import _gcp_secure_replica_bucket_name
    from app.utils.config import settings

    csp_u = (csp or "").strip().upper()
    if csp_u == "GCP":
        return _gcp_secure_replica_bucket_name()
    if csp_u == "AZURE":
        return (settings.AZURE_SECURE_REPLICA_CONTAINER_NAME or "").strip()
    return (settings.REPLICA_S3_BUCKET_NAME or "").strip()


def is_platform_secure_replica(csp: str, bucket_or_container: str) -> bool:
    replica = platform_secure_replica_name(csp)
    return bool(replica and bucket_or_container and bucket_or_container == replica)


def put_secure_vault_object(
    storage: SecureVaultStorage,
    object_key: str,
    body: bytes,
    *,
    server_side_encryption: bool = False,
    metadata: Optional[dict] = None,
    replicate: bool = True,
) -> None:
    if isinstance(storage, SecureAwsStorage):
        put_secure_object_dual(
            storage,
            object_key,
            body,
            server_side_encryption=server_side_encryption,
            metadata=metadata,
            replicate=replicate,
        )
        return

    if isinstance(storage, SecureGcpStorage):
        blob = storage.client.bucket(storage.bucket_name).blob(object_key)
        blob.metadata = metadata or {}
        blob.upload_from_string(body, content_type="application/octet-stream")
        if replicate and storage.replica_bucket:
            replica_blob = storage.client.bucket(storage.replica_bucket).blob(object_key)
            replica_blob.metadata = metadata or {}
            replica_blob.upload_from_string(body, content_type="application/octet-stream")
        return

    blob_client = storage.blob_service.get_blob_client(
        container=storage.container_name, blob=object_key
    )
    blob_client.upload_blob(
        body,
        overwrite=True,
        metadata=metadata or {},
    )
    if replicate and storage.replica_container:
        replica_client = storage.blob_service.get_blob_client(
            container=storage.replica_container, blob=object_key
        )
        replica_client.upload_blob(
            body,
            overwrite=True,
            metadata=metadata or {},
        )


def secure_replica_bucket_name(storage: SecureVaultStorage) -> Optional[str]:
    if isinstance(storage, SecureAwsStorage):
        return storage.replica_bucket if storage.dual_write_enabled else None
    if isinstance(storage, SecureGcpStorage):
        return storage.replica_bucket
    if isinstance(storage, SecureAzureStorage):
        return storage.replica_container
    return None


def secure_primary_bucket_name(storage: SecureVaultStorage) -> str:
    if isinstance(storage, SecureAwsStorage):
        return storage.primary_bucket
    if isinstance(storage, SecureGcpStorage):
        return storage.bucket_name
    return storage.container_name


def _aws_object_exists(client: Any, bucket: str, object_key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        client.head_object(Bucket=bucket, Key=object_key)
        return True
    except ClientError:
        return False


def archive_secure_vault_object(storage: SecureVaultStorage, object_key: str) -> str:
    """
    Move a vault object off the primary bucket/container into the replica vault.
    Returns the replica bucket/container name.
    """
    replica = secure_replica_bucket_name(storage)
    if not replica:
        raise SecureVaultArchiveError(
            "Archive requires a replica vault. Enable replication on upload or use platform secure storage."
        )

    if isinstance(storage, SecureAwsStorage):
        on_primary = _aws_object_exists(
            storage.primary_client, storage.primary_bucket, object_key
        )
        on_replica = _aws_object_exists(storage.replica_client, replica, object_key)
        if not on_primary and on_replica:
            return replica
        if not on_primary and not on_replica:
            raise SecureVaultArchiveError("File not found in secure vault.")
        if on_primary and not on_replica:
            copy_secure_object_to_replica(
                storage, object_key, server_side_encryption=True
            )
        storage.primary_client.delete_object(
            Bucket=storage.primary_bucket, Key=object_key
        )
        return replica

    if isinstance(storage, SecureGcpStorage):
        primary_bkt = storage.client.bucket(storage.bucket_name)
        replica_bkt = storage.client.bucket(replica)
        primary_blob = primary_bkt.blob(object_key)
        replica_blob = replica_bkt.blob(object_key)
        if not primary_blob.exists() and replica_blob.exists():
            return replica
        if not primary_blob.exists() and not replica_blob.exists():
            raise SecureVaultArchiveError("File not found in secure vault.")
        if primary_blob.exists() and not replica_blob.exists():
            replica_bkt.copy_blob(primary_blob, replica_bkt, object_key)
        if primary_blob.exists():
            primary_blob.delete()
        return replica

    primary_client = storage.blob_service.get_blob_client(
        container=storage.container_name, blob=object_key
    )
    replica_client = storage.blob_service.get_blob_client(
        container=replica, blob=object_key
    )
    primary_exists = primary_client.exists()
    replica_exists = replica_client.exists()
    if not primary_exists and replica_exists:
        return replica
    if not primary_exists and not replica_exists:
        raise SecureVaultArchiveError("File not found in secure vault.")
    if primary_exists and not replica_exists:
        replica_client.start_copy_from_url(primary_client.url)
    if primary_exists:
        primary_client.delete_blob()
    return replica


def _delete_replica_vault_object(storage: SecureVaultStorage, object_key: str) -> None:
    """Remove object from replica bucket/container only."""
    replica = secure_replica_bucket_name(storage)
    if not replica:
        return
    if isinstance(storage, SecureAwsStorage):
        if storage.replica_client:
            storage.replica_client.delete_object(Bucket=replica, Key=object_key)
        return
    if isinstance(storage, SecureGcpStorage):
        storage.client.bucket(replica).blob(object_key).delete()
        return
    storage.blob_service.get_blob_client(container=replica, blob=object_key).delete_blob()


def restore_secure_vault_object(storage: SecureVaultStorage, object_key: str) -> str:
    """
    Move a vault object from replica back to primary and remove the replica copy.
    Returns the primary bucket/container name.
    """
    replica = secure_replica_bucket_name(storage)
    primary = secure_primary_bucket_name(storage)
    if not replica:
        raise SecureVaultArchiveError(
            "Restore requires a replica vault where the archived copy is stored."
        )

    if isinstance(storage, SecureAwsStorage):
        if not _aws_object_exists(storage.replica_client, replica, object_key):
            if _aws_object_exists(storage.primary_client, primary, object_key):
                _delete_replica_vault_object(storage, object_key)
                return primary
            raise SecureVaultArchiveError("Archived copy not found in replica vault.")
        copy_secure_object_from_replica(
            storage, object_key, server_side_encryption=True
        )
        _delete_replica_vault_object(storage, object_key)
        return primary

    if isinstance(storage, SecureGcpStorage):
        primary_bkt = storage.client.bucket(primary)
        replica_bkt = storage.client.bucket(replica)
        replica_blob = replica_bkt.blob(object_key)
        primary_blob = primary_bkt.blob(object_key)
        if not replica_blob.exists():
            if primary_blob.exists():
                _delete_replica_vault_object(storage, object_key)
                return primary
            raise SecureVaultArchiveError("Archived copy not found in replica vault.")
        primary_bkt.copy_blob(replica_blob, primary_bkt, object_key)
        _delete_replica_vault_object(storage, object_key)
        return primary

    replica_client = storage.blob_service.get_blob_client(
        container=replica, blob=object_key
    )
    primary_client = storage.blob_service.get_blob_client(
        container=primary, blob=object_key
    )
    if not replica_client.exists():
        if primary_client.exists():
            _delete_replica_vault_object(storage, object_key)
            return primary
        raise SecureVaultArchiveError("Archived copy not found in replica vault.")
    body = replica_client.download_blob().readall()
    primary_client.upload_blob(body, overwrite=True)
    _delete_replica_vault_object(storage, object_key)
    return primary


def _delete_gcp_blob_if_exists(client: Any, bucket_name: str, object_key: str) -> None:
    blob = client.bucket(bucket_name).blob(object_key)
    if blob.exists():
        blob.delete()


def _delete_azure_blob_if_exists(blob_service: Any, container: str, object_key: str) -> None:
    blob_client = blob_service.get_blob_client(container=container, blob=object_key)
    try:
        if blob_client.exists():
            blob_client.delete_blob()
    except Exception as exc:
        err_name = type(exc).__name__
        if err_name not in ("ResourceNotFoundError",) and "BlobNotFound" not in str(exc):
            raise


def delete_secure_vault_object(storage: SecureVaultStorage, object_key: str) -> None:
    """Delete from primary and replica secure vault locations (tri-cloud)."""
    if isinstance(storage, SecureAwsStorage):
        delete_secure_object_dual(storage, object_key)
        return
    if isinstance(storage, SecureGcpStorage):
        _delete_gcp_blob_if_exists(storage.client, storage.bucket_name, object_key)
        if storage.replica_bucket:
            _delete_gcp_blob_if_exists(storage.client, storage.replica_bucket, object_key)
        return
    _delete_azure_blob_if_exists(
        storage.blob_service, storage.container_name, object_key
    )
    if storage.replica_container:
        _delete_azure_blob_if_exists(
            storage.blob_service, storage.replica_container, object_key
        )


def download_secure_vault_bytes(
    storage: SecureVaultStorage,
    object_key: str,
    username: str,
    *,
    bucket_override: Optional[str] = None,
    region_override: Optional[str] = None,
) -> bytes:
    if isinstance(storage, SecureAwsStorage):
        target = bucket_override or storage.primary_bucket
        if bucket_override and bucket_override != storage.primary_bucket:
            from app.storage.cloud_credentials import build_aws_s3_client_for_bucket

            client, _ = build_aws_s3_client_for_bucket(
                username, region_override or storage.region
            )
        else:
            client = storage.primary_client
        resp = client.get_object(Bucket=target, Key=object_key)
        return resp["Body"].read()

    if isinstance(storage, SecureGcpStorage):
        bucket = bucket_override or storage.bucket_name
        return storage.client.bucket(bucket).blob(object_key).download_as_bytes()

    container = bucket_override or storage.container_name
    return (
        storage.blob_service.get_blob_client(container=container, blob=object_key)
        .download_blob()
        .readall()
    )


def presigned_secure_download_url(
    storage: SecureVaultStorage,
    object_key: str,
    username: str,
    *,
    bucket_override: Optional[str] = None,
    region_override: Optional[str] = None,
) -> str:
    if isinstance(storage, SecureAwsStorage):
        from app.storage.cloud_credentials import build_aws_s3_client_for_bucket

        target = bucket_override or storage.primary_bucket
        if bucket_override and bucket_override != storage.primary_bucket:
            client, _ = build_aws_s3_client_for_bucket(
                username, region_override or storage.region
            )
        else:
            client = storage.primary_client
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": target, "Key": object_key},
            ExpiresIn=3600,
        )

    if isinstance(storage, SecureGcpStorage):
        bucket = bucket_override or storage.bucket_name
        blob = storage.client.bucket(bucket).blob(object_key)
        return blob.generate_signed_url(expiration=timedelta(hours=1))

    from azure.storage.blob import BlobSasPermissions, generate_blob_sas
    from datetime import datetime, timezone

    from app.byoc.credential_resolver import resolve_azure_credentials

    azure_creds = resolve_azure_credentials(username)
    container = bucket_override or storage.container_name
    account_name = azure_creds.get("account_name") or storage.blob_service.account_name
    account_key = azure_creds.get("account_key", "")
    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=object_key,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{container}/{object_key}?{sas}"
    )
