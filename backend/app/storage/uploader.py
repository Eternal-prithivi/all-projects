# This file contains the specialized functions for uploading a file to each CSP.

from fastapi import UploadFile
from google.cloud import storage as gcp_storage
from azure.storage.blob import BlobServiceClient, StandardBlobTier
import boto3
import os
from app.utils.config import settings

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_to_aws(file: UploadFile, username: str, filename: str, storage_class: str):
    """Uploads a file to the configured AWS S3 bucket with a specific storage class."""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    object_key = f"{username}/{filename}"
    
    aws_storage_class_map = {
        "S3 Standard": "STANDARD",
        "S3 Standard-IA": "STANDARD_IA",
        "S3 Glacier Flexible": "GLACIER" 
    }
    api_storage_class = aws_storage_class_map.get(storage_class, "STANDARD")

    s3_client.upload_fileobj(
        file.file, 
        settings.S3_BUCKET_NAME, 
        object_key,
        ExtraArgs={'StorageClass': api_storage_class}
    )
    return object_key

def upload_to_gcp(file: UploadFile, username: str, filename: str, storage_class: str):
    """Uploads a file to the configured GCP Cloud Storage bucket with a specific storage class."""
    
    gcp_key_path = settings.GCP_SERVICE_ACCOUNT_JSON_PATH
    logger.info(f"Attempting GCP upload for {filename} by {username}")
    logger.info(f"GCP Key Path from settings: {gcp_key_path}")

    # --- NEW: Explicit path existence and readability checks ---
    if not os.path.exists(gcp_key_path):
        logger.error(f"GCP Key File NOT FOUND at path: {gcp_key_path}")
        raise FileNotFoundError(f"GCP Key File not found: {gcp_key_path}")
    if not os.path.isfile(gcp_key_path):
        logger.error(f"GCP Key Path exists but is NOT a file: {gcp_key_path}")
        raise ValueError(f"GCP Key Path is not a file: {gcp_key_path}")
    
    # Try reading the file directly to check permissions
    try:
        with open(gcp_key_path, 'r') as f:
            f.read(1) # Try reading just one byte
        logger.info(f"Successfully read a byte from GCP Key File: {gcp_key_path}")
    except Exception as e:
        logger.error(f"PERMISSION DENIED or ERROR READING GCP Key File: {gcp_key_path} - Error: {e}")
        raise PermissionError(f"Cannot read GCP Key File: {gcp_key_path}. Check permissions. Original error: {e}")


    try:
        logger.info("Attempting to initialize GCP Storage Client...")
        storage_client = gcp_storage.Client.from_service_account_json(gcp_key_path)
        logger.info("GCP Storage Client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize GCP Storage Client: {e}")
        raise

    try:
        bucket = storage_client.bucket(settings.GCP_BUCKET_NAME)
        logger.info(f"Accessing GCP bucket: {settings.GCP_BUCKET_NAME}")
        # --- NEW: Check if the bucket exists and is accessible ---
        if not bucket.exists():
            logger.error(f"GCP Bucket '{settings.GCP_BUCKET_NAME}' does not exist or is not accessible with provided credentials.")
            raise ValueError(f"GCP Bucket '{settings.GCP_BUCKET_NAME}' does not exist or is not accessible.")
    except Exception as e:
        logger.error(f"Error accessing GCP bucket '{settings.GCP_BUCKET_NAME}': {e}")
        raise # Re-raise to show the error

    object_key = f"{username}/{filename}"
    blob = bucket.blob(object_key)
    
    gcp_storage_class_map = {
        "Standard Storage": "STANDARD",
        "Nearline Storage": "NEARLINE",
        "Archive Storage": "ARCHIVE"
    }
    api_storage_class = gcp_storage_class_map.get(storage_class, "STANDARD")

    blob.storage_class = api_storage_class
    logger.info(f"Setting GCP storage class to: {api_storage_class}")

    file.file.seek(0)
    logger.info(f"Attempting to upload file {object_key} to GCP...")
    
    try:
        blob.upload_from_file(file.file)
        logger.info(f"File {object_key} uploaded successfully to GCP.")
    except Exception as e:
        logger.error(f"Error during GCP file upload for {object_key}: {e}")
        raise # Re-raise to show the error
    
    return object_key

def upload_to_azure(file: UploadFile, username: str, filename: str, storage_class: str):
    """Uploads a file to the configured Azure Blob Storage container with a specific storage class."""
    connection_string = (
        f"DefaultEndpointsProtocol=https;AccountName={settings.AZURE_STORAGE_ACCOUNT_NAME};"
        f"AccountKey={settings.AZURE_STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
    )
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    object_key = f"{username}/{filename}"
    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_CONTAINER_NAME, blob=object_key
    )

    azure_storage_class_map = {
        "Hot Blob Storage": StandardBlobTier.Hot,
        "Cool Blob Storage": StandardBlobTier.Cool,
        "Archive Storage": StandardBlobTier.Archive
    }
    api_storage_class = azure_storage_class_map.get(storage_class, StandardBlobTier.Hot)
    
    file.file.seek(0)
    blob_client.upload_blob(file.file, overwrite=True, standard_blob_tier=api_storage_class)
    return object_key

