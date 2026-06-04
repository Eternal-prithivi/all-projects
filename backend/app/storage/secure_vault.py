"""Multi-cloud secure vault storage (AWS SSE dual-write, GCS, Azure Blob)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional, Union

from app.cloud.providers import CloudProvider, normalize_provider
from app.storage.cloud_credentials import (
    SecureAwsStorage,
    build_azure_blob_service,
    build_gcp_storage_client,
    delete_secure_object_dual,
    put_secure_object_dual,
    resolve_secure_aws_storage,
)

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

    def object_key(self, username: str, filename: str) -> str:
        return f"{self.list_prefix}{filename}"

    @property
    def primary_bucket(self) -> str:
        return self.container_name

    @property
    def region(self) -> str:
        return ""


def resolve_secure_gcp_storage(username: str) -> SecureGcpStorage:
    from app.utils.config import settings

    client, bucket_name, is_byoc = build_gcp_storage_client(username)
    prefix = f"{username}/" if is_byoc else f"secure/{username}/"
    project_id = getattr(client, "project", None) or ""
    replica_bucket: Optional[str] = None
    if is_byoc:
        from app.byoc.credential_resolver import get_user_cloud_credentials

        byoc = get_user_cloud_credentials(username, "GCP")
        if byoc:
            replica = (byoc.get("replica_bucket_name") or "").strip()
            if replica:
                replica_bucket = replica
    else:
        replica = (getattr(settings, "GCP_REPLICA_BUCKET_NAME", None) or "").strip()
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
    blob_service, container_name, is_byoc = build_azure_blob_service(username)
    prefix = f"{username}/" if is_byoc else f"secure/{username}/"
    return SecureAzureStorage(
        blob_service=blob_service,
        container_name=container_name,
        is_byoc=is_byoc,
        list_prefix=prefix,
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
    return False


def vault_csp(storage: SecureVaultStorage) -> str:
    if isinstance(storage, SecureAwsStorage):
        return "AWS"
    if isinstance(storage, SecureGcpStorage):
        return "GCP"
    return "Azure"


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


def delete_secure_vault_object(storage: SecureVaultStorage, object_key: str) -> None:
    if isinstance(storage, SecureAwsStorage):
        delete_secure_object_dual(storage, object_key)
        return
    if isinstance(storage, SecureGcpStorage):
        storage.client.bucket(storage.bucket_name).blob(object_key).delete()
        if storage.replica_bucket:
            storage.client.bucket(storage.replica_bucket).blob(object_key).delete()
        return
    storage.blob_service.get_blob_client(
        container=storage.container_name, blob=object_key
    ).delete_blob()


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
