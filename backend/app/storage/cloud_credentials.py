"""
Build per-user cloud clients using BYOC credentials when configured,
otherwise Zenith platform defaults from settings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import boto3
from azure.storage.blob import BlobServiceClient
from botocore.config import Config
from google.cloud import storage as gcp_storage
from google.oauth2 import service_account

from app.byoc.credential_resolver import (
    get_aws_bucket_layout,
    resolve_aws_credentials,
    resolve_azure_credentials,
    resolve_gcp_credentials,
)
from app.utils.config import settings

S3_CONFIG_V4 = Config(signature_version="s3v4")


def _aws_client_kwargs(aws: dict) -> dict:
    kwargs: dict = {
        "aws_access_key_id": aws["access_key_id"],
        "aws_secret_access_key": aws["secret_access_key"],
        "region_name": aws.get("region") or settings.PRIMARY_S3_REGION,
        "config": S3_CONFIG_V4,
    }
    session_token = aws.get("session_token")
    if session_token:
        kwargs["aws_session_token"] = session_token
    return kwargs


def build_aws_s3_client(username: str) -> Tuple[Any, str, bool]:
    """Return (boto3 S3 client, bucket_name, is_byoc)."""
    aws = resolve_aws_credentials(username)
    client = boto3.client("s3", **_aws_client_kwargs(aws))
    return client, aws["bucket_name"], bool(aws.get("is_byoc"))


def build_aws_ce_client(username: str) -> Tuple[Any, bool]:
    """Return (boto3 Cost Explorer client, is_byoc)."""
    aws = resolve_aws_credentials(username)
    client = boto3.client("ce", **_aws_client_kwargs(aws))
    return client, bool(aws.get("is_byoc"))


@dataclass
class SecureAwsStorage:
    """Primary (+ optional replica) S3 clients for the secure vault."""

    primary_client: Any
    replica_client: Optional[Any]
    primary_bucket: str
    replica_bucket: Optional[str]
    region: str
    is_byoc: bool
    list_prefix: str
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None
    dedicated_secure_bucket: bool = False

    def object_key(self, username: str, filename: str) -> str:
        if self.is_byoc and not self.dedicated_secure_bucket:
            return f"secure/{username}/{filename}"
        return f"{username}/{filename}"

    @property
    def dual_write_enabled(self) -> bool:
        return bool(self.replica_client and self.replica_bucket)


def put_secure_object_dual(
    storage: SecureAwsStorage,
    object_key: str,
    body: bytes,
    *,
    server_side_encryption: bool = False,
    metadata: Optional[dict] = None,
) -> None:
    """Write to primary secure bucket and replica when BYOC/platform dual-write is on."""
    put_kwargs: dict = {
        "Bucket": storage.primary_bucket,
        "Key": object_key,
        "Body": body,
    }
    if server_side_encryption:
        put_kwargs["ServerSideEncryption"] = "AES256"
    if metadata:
        put_kwargs["Metadata"] = metadata
    storage.primary_client.put_object(**put_kwargs)

    if not storage.dual_write_enabled:
        return

    replica_kwargs: dict = {
        "Bucket": storage.replica_bucket,
        "Key": object_key,
        "Body": body,
    }
    if server_side_encryption:
        replica_kwargs["ServerSideEncryption"] = "AES256"
    if metadata:
        replica_kwargs["Metadata"] = metadata
    storage.replica_client.put_object(**replica_kwargs)


def copy_secure_object_to_replica(
    storage: SecureAwsStorage,
    object_key: str,
    *,
    server_side_encryption: bool = False,
) -> None:
    """Copy an object from primary secure bucket to replica (cross-region when configured)."""
    if not storage.dual_write_enabled:
        return
    copy_source = f"{storage.primary_bucket}/{object_key}"
    kwargs: dict = {
        "Bucket": storage.replica_bucket,
        "Key": object_key,
        "CopySource": copy_source,
    }
    if server_side_encryption:
        kwargs["ServerSideEncryption"] = "AES256"
        kwargs["MetadataDirective"] = "REPLACE"
    storage.replica_client.copy_object(**kwargs)


def delete_secure_object_dual(storage: SecureAwsStorage, object_key: str) -> None:
    """Delete from primary and replica secure buckets."""
    storage.primary_client.delete_object(
        Bucket=storage.primary_bucket, Key=object_key
    )
    if storage.dual_write_enabled:
        storage.replica_client.delete_object(
            Bucket=storage.replica_bucket, Key=object_key
        )


def resolve_secure_aws_storage(username: str) -> SecureAwsStorage:
    """
    Secure vault targets the user's BYOC bucket (prefix secure/{user}/) when connected;
    otherwise Zenith dedicated secure + replica buckets ({user}/).
    """
    aws = resolve_aws_credentials(username)
    if aws.get("is_byoc"):
        layout = get_aws_bucket_layout(username) or {}
        secure_bucket = layout.get("secure_bucket_name") or aws["bucket_name"]
        primary_region = layout.get("primary_region") or aws.get("region") or settings.PRIMARY_S3_REGION
        replica_bucket = layout.get("replica_bucket_name") or ""
        replica_region = layout.get("replica_region") or settings.REPLICA_S3_REGION
        dual_write = layout.get("secure_dual_write", True)
        dedicated = bool(
            layout.get("secure_bucket_name")
            and layout.get("secure_bucket_name") != layout.get("storage_bucket_name")
        )

        primary = boto3.client("s3", **_aws_client_kwargs(aws))

        replica_client = None
        if dual_write and replica_bucket:
            replica_kwargs = _aws_client_kwargs(aws)
            replica_kwargs["region_name"] = replica_region
            replica_client = boto3.client("s3", **replica_kwargs)

        list_prefix = (
            f"{username}/" if dedicated else f"secure/{username}/"
        )

        return SecureAwsStorage(
            primary_client=primary,
            replica_client=replica_client,
            primary_bucket=secure_bucket,
            replica_bucket=replica_bucket if replica_client else None,
            region=primary_region,
            is_byoc=True,
            list_prefix=list_prefix,
            access_key_id=aws["access_key_id"],
            secret_access_key=aws["secret_access_key"],
            session_token=aws.get("session_token"),
            dedicated_secure_bucket=dedicated,
        )

    primary = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.PRIMARY_S3_REGION,
        config=S3_CONFIG_V4,
    )
    replica = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REPLICA_S3_REGION,
        config=S3_CONFIG_V4,
    )
    return SecureAwsStorage(
        primary_client=primary,
        replica_client=replica,
        primary_bucket=settings.SECURE_S3_BUCKET_NAME,
        replica_bucket=settings.REPLICA_S3_BUCKET_NAME,
        region=settings.PRIMARY_S3_REGION,
        is_byoc=False,
        list_prefix=f"{username}/",
        access_key_id=settings.AWS_ACCESS_KEY_ID,
        secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        session_token=None,
    )


def build_gcp_storage_client(username: str) -> Tuple[gcp_storage.Client, str, bool]:
    """Return (GCS client, bucket_name, is_byoc)."""
    gcp = resolve_gcp_credentials(username)
    if gcp.get("is_byoc"):
        sa_json = gcp.get("service_account_json") or ""
        if isinstance(sa_json, str):
            sa_info = json.loads(sa_json)
        else:
            sa_info = sa_json
        credentials = service_account.Credentials.from_service_account_info(sa_info)
        client = gcp_storage.Client(
            credentials=credentials,
            project=sa_info.get("project_id"),
        )
        return client, gcp["bucket_name"], True

    client = gcp_storage.Client.from_service_account_json(
        gcp["service_account_key_path"]
    )
    return client, gcp["bucket_name"], False


def build_azure_blob_service(username: str) -> Tuple[BlobServiceClient, str, bool]:
    """Return (BlobServiceClient, container_name, is_byoc)."""
    azure = resolve_azure_credentials(username)
    connection_string = (
        "DefaultEndpointsProtocol=https;"
        f"AccountName={azure['account_name']};"
        f"AccountKey={azure['account_key']};"
        "EndpointSuffix=core.windows.net"
    )
    client = BlobServiceClient.from_connection_string(connection_string)
    return client, azure["container_name"], bool(azure.get("is_byoc"))
