# This file contains the specialized functions for uploading a file to each CSP.

import logging

import boto3
from azure.storage.blob import BlobServiceClient, StandardBlobTier
from fastapi import UploadFile
from google.cloud import storage as gcp_storage

from app.storage.cloud_credentials import (
    build_aws_s3_client,
    build_aws_s3_client_for_bucket,
    build_azure_blob_service,
    build_gcp_storage_client,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upload_to_aws(
    file: UploadFile,
    username: str,
    filename: str,
    storage_class: str,
    *,
    bucket_name: str | None = None,
    region_name: str | None = None,
):
    """Uploads a file to the user's resolved AWS S3 bucket (BYOC or platform)."""
    if bucket_name and region_name:
        s3_client, is_byoc = build_aws_s3_client_for_bucket(username, region_name)
        target_bucket = bucket_name
    else:
        s3_client, target_bucket, is_byoc = build_aws_s3_client(username)
    bucket_name = target_bucket
    object_key = f"{username}/{filename}"

    aws_storage_class_map = {
        "S3 Standard": "STANDARD",
        "S3 Standard-IA": "STANDARD_IA",
        "S3 Glacier Flexible": "GLACIER",
    }
    api_storage_class = aws_storage_class_map.get(storage_class, "STANDARD")

    file.file.seek(0)
    s3_client.upload_fileobj(
        file.file,
        bucket_name,
        object_key,
        ExtraArgs={"StorageClass": api_storage_class},
    )
    logger.info(
        "Uploaded %s to s3://%s/%s (byoc=%s)",
        filename,
        bucket_name,
        object_key,
        is_byoc,
    )
    return object_key


def upload_to_gcp(file: UploadFile, username: str, filename: str, storage_class: str):
    """Uploads a file to the user's resolved GCP bucket (BYOC or platform)."""
    storage_client, bucket_name, is_byoc = build_gcp_storage_client(username)
    bucket = storage_client.bucket(bucket_name)
    if not bucket.exists():
        raise ValueError(
            f"GCP bucket '{bucket_name}' does not exist or is not accessible with the configured credentials."
        )

    object_key = f"{username}/{filename}"
    blob = bucket.blob(object_key)

    gcp_storage_class_map = {
        "Standard Storage": "STANDARD",
        "STANDARD": "STANDARD",
        "Nearline Storage": "NEARLINE",
        "NEARLINE": "NEARLINE",
        "Archive Storage": "ARCHIVE",
        "ARCHIVE": "ARCHIVE",
    }
    api_storage_class = gcp_storage_class_map.get(storage_class, "STANDARD")
    blob.storage_class = api_storage_class

    file.file.seek(0)
    blob.upload_from_file(file.file)
    logger.info(
        "Uploaded %s to gs://%s/%s (byoc=%s)",
        filename,
        bucket_name,
        object_key,
        is_byoc,
    )
    return object_key


def upload_to_azure(file: UploadFile, username: str, filename: str, storage_class: str):
    """Uploads a file to the user's resolved Azure container (BYOC or platform)."""
    blob_service_client, container_name, is_byoc = build_azure_blob_service(username)
    object_key = f"{username}/{filename}"
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=object_key
    )

    azure_storage_class_map = {
        "Hot Blob Storage": StandardBlobTier.Hot,
        "Hot": StandardBlobTier.Hot,
        "Cool Blob Storage": StandardBlobTier.Cool,
        "Cool": StandardBlobTier.Cool,
        "Archive Storage": StandardBlobTier.Archive,
        "Archive": StandardBlobTier.Archive,
    }
    api_storage_class = azure_storage_class_map.get(storage_class, StandardBlobTier.Hot)

    file.file.seek(0)
    blob_client.upload_blob(file.file, overwrite=True, standard_blob_tier=api_storage_class)
    logger.info(
        "Uploaded %s to azure://%s/%s (byoc=%s)",
        filename,
        container_name,
        object_key,
        is_byoc,
    )
    return object_key
