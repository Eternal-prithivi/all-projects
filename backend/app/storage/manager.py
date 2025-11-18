# This file contains the specialized functions for accessing and managing files on each CSP.

import boto3
from google.cloud import storage as gcp_storage
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta
from botocore.config import Config
from fastapi import HTTPException, status # <--- ADD THIS IMPORT!

from app.utils.config import settings

# --- AWS Specialist Functions ---

# Create a common S3 configuration for Signature Version 4
s3_config_v4 = Config(
    signature_version='s3v4'
)

# Centralized AWS S3 client for ALL regular storage operations
# This client should be configured once and used by all AWS functions in this file.
s3_client_regular = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.PRIMARY_S3_REGION, # <--- Use PRIMARY_S3_REGION here
    config=s3_config_v4
)

def delete_from_aws(object_key: str):
    """Deletes an object from the configured AWS S3 bucket."""
    # Use the centralized s3_client_regular
    # You were initializing a new client and using settings.S3_BUCKET_NAME
    s3_client_regular.delete_object(Bucket=settings.REGULAR_S3_BUCKET_NAME, Key=object_key) # <--- Use REGULAR_S3_BUCKET_NAME
    print(f"Successfully deleted {object_key} from AWS S3.")


def get_download_url_from_aws(object_key: str) -> str:
    """
    Generates a pre-signed download URL for an object in AWS S3.
    Includes logic to check for Glacier and handle restoration status.
    """
    try:
        # Use the centralized s3_client_regular
        # Get object metadata to check storage class and restore status
        response = s3_client_regular.head_object(
            Bucket=settings.REGULAR_S3_BUCKET_NAME, # <--- Use REGULAR_S3_BUCKET_NAME
            Key=object_key
        )
        storage_class = response.get('StorageClass')
        restore_status = response.get('Restore') # e.g., 'ongoing-request="false", expiry-date="Mon, 27 Nov 2023 00:00:00 GMT"'

        # Handle Glacier/Deep Archive storage classes
        if storage_class == 'GLACIER' or storage_class == 'DEEP_ARCHIVE':
            if restore_status and 'ongoing-request="false"' in restore_status:
                # File is restored and ready for download
                print(f"INFO: Object '{object_key}' is in {storage_class} but already restored. Proceeding with download.")
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
        url = s3_client_regular.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.REGULAR_S3_BUCKET_NAME, 'Key': object_key}, # <--- Use REGULAR_S3_BUCKET_NAME
            ExpiresIn=3600 # URL valid for 1 hour
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
def initiate_glacier_restore_aws(object_key: str, tier: str = 'Standard', days: int = 7):
    """
    Initiates a restore request for an object in Glacier or Deep Archive storage class.
    Tier can be 'Expedited', 'Standard', or 'Bulk'.
    """
    try:
        s3_client_regular.restore_object(
            Bucket=settings.REGULAR_S3_BUCKET_NAME, # <--- Use REGULAR_S3_BUCKET_NAME
            Key=object_key,
            RestoreRequest={
                'Days': days, # How long the restored copy will be available (1-30 days)
                'GlacierJobParameters': {
                    'Tier': tier # 'Expedited', 'Standard', or 'Bulk'
                }
            }
        )
        return {"message": f"Restore initiated for '{object_key}' with {tier} tier. It will be available for {days} days."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate restore for '{object_key}': {e}"
        )


def upload_to_aws(file, username: str, filename: str, storage_class: str):
    """Uploads a file to AWS S3 with a specified storage class."""
    object_key = f"{username}/{filename}"
    try:
        s3_client_regular.upload_fileobj(
            file.file,
            settings.REGULAR_S3_BUCKET_NAME, # <--- Use REGULAR_S3_BUCKET_NAME
            object_key,
            ExtraArgs={'StorageClass': storage_class}
        )
        return object_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload '{filename}' to AWS S3: {e}"
        )


def change_tier_on_aws(object_key: str, new_tier: str):
    """Changes the storage class of an object in AWS S3."""
    # Use the centralized s3_client_regular
    # You were initializing a new client and using settings.S3_BUCKET_NAME
    try:
        s3_client_regular.copy_object(
            Bucket=settings.REGULAR_S3_BUCKET_NAME, # <--- Use REGULAR_S3_BUCKET_NAME
            Key=object_key,
            CopySource={'Bucket': settings.REGULAR_S3_BUCKET_NAME, 'Key': object_key}, # <--- Use REGULAR_S3_BUCKET_NAME
            StorageClass=new_tier,
            MetadataDirective='COPY' # This ensures metadata is preserved
        )
        print(f"Successfully tiered {object_key} to {new_tier} on AWS S3.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change tier for '{object_key}' to '{new_tier}' on AWS S3: {e}"
        )


# --- GCP Specialist Functions ---

def delete_from_gcp(object_key: str):
    """Deletes an object from the configured GCP Cloud Storage bucket."""
    storage_client = gcp_storage.Client.from_service_account_json(
        settings.GCP_SERVICE_ACCOUNT_JSON_PATH
    )
    bucket = storage_client.bucket(settings.GCP_BUCKET_NAME)
    blob = bucket.blob(object_key)
    blob.delete()
    print(f"Successfully deleted {object_key} from GCP Cloud Storage.")

def get_download_url_from_gcp(object_key: str) -> str:
    """Generates a pre-signed download URL for an object in GCP Cloud Storage."""
    storage_client = gcp_storage.Client.from_service_account_json(
        settings.GCP_SERVICE_ACCOUNT_JSON_PATH
    )
    bucket = storage_client.bucket(settings.GCP_BUCKET_NAME)
    blob = bucket.blob(object_key)
    url = blob.generate_signed_url(expiration=timedelta(hours=1))
    return url

# --- NEW: Function to change storage tier on GCP ---
def change_tier_on_gcp(object_key: str, new_tier: str):
    """Changes the storage class of an object in GCP Cloud Storage."""
    storage_client = gcp_storage.Client.from_service_account_json(
        settings.GCP_SERVICE_ACCOUNT_JSON_PATH
    )
    bucket = storage_client.bucket(settings.GCP_BUCKET_NAME)
    blob = bucket.blob(object_key)
    blob.update_storage_class(new_tier)
    print(f"Successfully tiered {object_key} to {new_tier} on GCP Cloud Storage.")


# --- Azure Specialist Functions ---

def delete_from_azure(object_key: str):
    """Deletes an object from the configured Azure Blob Storage container."""
    connection_string = (
        f"DefaultEndpointsProtocol=https;AccountName={settings.AZURE_STORAGE_ACCOUNT_NAME};"
        f"AccountKey={settings.AZURE_STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
    )
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_CONTAINER_NAME, blob=object_key
    )
    blob_client.delete_blob()
    print(f"Successfully deleted {object_key} from Azure Blob Storage.")

def get_download_url_from_azure(object_key: str) -> str:
    """Generates a pre-signed download URL for an object in Azure Blob Storage."""
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
    
    sas_token = generate_blob_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        container_name=settings.AZURE_CONTAINER_NAME,
        blob_name=object_key,
        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    url = (
        f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
        f"{settings.AZURE_CONTAINER_NAME}/{object_key}?{sas_token}"
    )
    return url

# --- NEW: Function to change storage tier on Azure ---
def change_tier_on_azure(object_key: str, new_tier: str):
    """Changes the access tier of an object in Azure Blob Storage."""
    connection_string = (
        f"DefaultEndpointsProtocol=https;AccountName={settings.AZURE_STORAGE_ACCOUNT_NAME};"
        f"AccountKey={settings.AZURE_STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
    )
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_CONTAINER_NAME, blob=object_key
    )
    blob_client.set_standard_blob_tier(new_tier)
    print(f"Successfully tiered {object_key} to {new_tier} on Azure Blob Storage.")