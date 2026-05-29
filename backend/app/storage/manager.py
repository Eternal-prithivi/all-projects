# This file contains the specialized functions for accessing and managing files on each CSP.

import boto3
from datetime import datetime, timedelta
from botocore.config import Config
from fastapi import HTTPException, status
from app.byoc.credential_resolver import resolve_azure_credentials
from app.storage.cloud_credentials import (
    S3_CONFIG_V4,
    build_aws_s3_client,
    build_azure_blob_service,
    build_gcp_storage_client,
)
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# --- AWS Specialist Functions ---

def list_objects_aws(
    *,
    bucket_name: str,
    prefix: str,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None = None,
    region_name: str | None = None,
    max_keys: int = 1000,
) -> list[dict]:
    """
    List objects for a given prefix in S3.

    Returns a list of dicts: {object_key, size_bytes, last_modified}
    """
    client = boto3.client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
        region_name=region_name or settings.PRIMARY_S3_REGION,
        config=S3_CONFIG_V4,
    )

    results: list[dict] = []
    continuation_token: str | None = None

    while True:
        kwargs: dict = {"Bucket": bucket_name, "Prefix": prefix, "MaxKeys": max_keys}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []) or []:
            results.append(
                {
                    "object_key": obj.get("Key", ""),
                    "size_bytes": int(obj.get("Size", 0) or 0),
                    "last_modified": obj.get("LastModified"),
                    "storage_class": obj.get("StorageClass"),
                }
            )

        if not resp.get("IsTruncated"):
            break

        continuation_token = resp.get("NextContinuationToken")

        # Hard-stop at max_keys per page * 10 pages to avoid runaway sync cost.
        if len(results) >= (max_keys * 10):
            break

    return results

def delete_from_aws(username: str, object_key: str):
    """Deletes an object from the user's resolved AWS S3 bucket."""
    s3_client, bucket_name, _ = build_aws_s3_client(username)
    s3_client.delete_object(Bucket=bucket_name, Key=object_key)
    logger.info(f"Deleted {object_key} from AWS S3 bucket {bucket_name}")


def get_download_url_from_aws(username: str, object_key: str) -> str:
    """
    Generates a pre-signed download URL for an object in AWS S3.
    Includes logic to check for Glacier and handle restoration status.
    """
    try:
        s3_client, bucket_name, _ = build_aws_s3_client(username)
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        storage_class = response.get('StorageClass')
        restore_status = response.get('Restore') # e.g., 'ongoing-request="false", expiry-date="Mon, 27 Nov 2023 00:00:00 GMT"'

        # Handle Glacier/Deep Archive storage classes
        if storage_class == 'GLACIER' or storage_class == 'DEEP_ARCHIVE':
            if restore_status and 'ongoing-request="false"' in restore_status:
                # File is restored and ready for download
                logger.info(f"Object '{object_key}' is in {storage_class} but already restored. Proceeding with download")
                pass # Fall through to generate_presigned_url
            elif restore_status and 'ongoing-request="true"' in restore_status:
                # File is currently being restored
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, # 409 Conflict
                    detail=f"File '{object_key}' is currently being restored from {storage_class}. Please try again later."
                )
            else:
                # File is in Glacier but not yet restored (or restore has expired)
                raise HTTPException(
                    status_code=status.HTTP_412_PRECONDITION_FAILED, # 412 Precondition Failed
                    detail=f"File '{object_key}' is in {storage_class} storage and needs to be restored before downloading. Initiate a restore operation first."
                )
        
        # If not Glacier, or if Glacier and already restored, proceed to generate URL
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=3600,
        )
        return url
    except HTTPException:
        raise # Re-raise our custom HTTPExceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing download for {object_key}: {e}"
        )

# --- NEW: Function to initiate Glacier restore on AWS ---
def initiate_glacier_restore_aws(username: str, object_key: str, tier: str = "Standard", days: int = 7):
    """
    Initiates a restore request for an object in Glacier or Deep Archive storage class.
    Tier can be 'Expedited', 'Standard', or 'Bulk'.
    """
    try:
        s3_client, bucket_name, _ = build_aws_s3_client(username)
        s3_client.restore_object(
            Bucket=bucket_name,
            Key=object_key,
            RestoreRequest={
                "Days": days,
                "GlacierJobParameters": {"Tier": tier},
            },
        )
        return {"message": f"Restore initiated for '{object_key}' with {tier} tier. It will be available for {days} days."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate restore for '{object_key}': {e}"
        )


def change_tier_on_aws(username: str, object_key: str, new_tier: str):
    """Changes the storage class of an object in AWS S3."""
    try:
        s3_client, bucket_name, _ = build_aws_s3_client(username)
        s3_client.copy_object(
            Bucket=bucket_name,
            Key=object_key,
            CopySource={"Bucket": bucket_name, "Key": object_key},
            StorageClass=new_tier,
            MetadataDirective="COPY",
        )
        logger.info(f"Tiered {object_key} to {new_tier} on AWS S3 bucket {bucket_name}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change tier for '{object_key}' to '{new_tier}' on AWS S3: {e}",
        )


# --- GCP Specialist Functions ---

def delete_from_gcp(username: str, object_key: str):
    """Deletes an object from the user's resolved GCP bucket."""
    storage_client, bucket_name, _ = build_gcp_storage_client(username)
    bucket = storage_client.bucket(bucket_name)
    bucket.blob(object_key).delete()
    logger.info(f"Deleted {object_key} from GCP bucket {bucket_name}")


def get_download_url_from_gcp(username: str, object_key: str) -> str:
    """Generates a pre-signed download URL for an object in GCP Cloud Storage."""
    storage_client, bucket_name, _ = build_gcp_storage_client(username)
    blob = storage_client.bucket(bucket_name).blob(object_key)
    return blob.generate_signed_url(expiration=timedelta(hours=1))


def change_tier_on_gcp(username: str, object_key: str, new_tier: str):
    """Changes the storage class of an object in GCP Cloud Storage."""
    storage_client, bucket_name, _ = build_gcp_storage_client(username)
    blob = storage_client.bucket(bucket_name).blob(object_key)
    blob.update_storage_class(new_tier)
    logger.info(f"Tiered {object_key} to {new_tier} on GCP bucket {bucket_name}")


# --- Azure Specialist Functions ---

def delete_from_azure(username: str, object_key: str):
    """Deletes an object from the user's resolved Azure container."""
    blob_service_client, container_name, _ = build_azure_blob_service(username)
    blob_service_client.get_blob_client(container=container_name, blob=object_key).delete_blob()
    logger.info(f"Deleted {object_key} from Azure container {container_name}")


def get_download_url_from_azure(username: str, object_key: str) -> str:
    """Generates a pre-signed download URL for an object in Azure Blob Storage."""
    from azure.storage.blob import BlobSasPermissions, generate_blob_sas

    azure = resolve_azure_credentials(username)
    container_name = azure["container_name"]
    account_name = azure["account_name"]
    account_key = azure["account_key"]

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=object_key,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1),
    )
    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{container_name}/{object_key}?{sas_token}"
    )


def change_tier_on_azure(username: str, object_key: str, new_tier: str):
    """Changes the access tier of an object in Azure Blob Storage."""
    blob_service_client, container_name, _ = build_azure_blob_service(username)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=object_key)
    blob_client.set_standard_blob_tier(new_tier)
    logger.info(f"Tiered {object_key} to {new_tier} on Azure container {container_name}")
