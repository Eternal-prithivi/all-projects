import boto3
import re
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pymongo.collection import Collection
from botocore.config import Config

from app.utils.config import settings
from app.auth.auth_utils import require_2fa
from app.users.user_model import UserInDB
from app.database.mongo_client import mongodb_client
from app.storage.models_storage import FileMetadata
from app.storage.tasks import process_secure_file

# The prefix is removed here as it is handled in main.py
router = APIRouter(tags=["Security"])

s3_config_v4 = Config(
    signature_version='s3v4'
)
# S3 clients for primary and replica buckets
s3_client_primary = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.PRIMARY_S3_REGION,
    config=s3_config_v4
)
s3_client_replica = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.REPLICA_S3_REGION,
    config=s3_config_v4
)
def get_secure_files_collection() -> Collection:
    return mongodb_client.get_collection("secure_files")

@router.post("/upload-secure", status_code=status.HTTP_202_ACCEPTED)
async def upload_secure_file(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    encrypt_manual: bool = Form(False),
    file: UploadFile = File(...)
):
    """
    Accepts a file for secure processing and uploads it to S3,
    then sends a background task to process it.
    """
    object_key = f"{user.username}/{file.filename}"

    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        s3_client_primary.upload_fileobj(file.file, settings.SECURE_S3_BUCKET_NAME, object_key)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Initial upload failed: {str(e)}")

    file_metadata = FileMetadata(
        filename=file.filename,
        s3_key=object_key,
        owner_username=user.username,
        size_bytes=file_size,
    )
    files_db.insert_one(file_metadata.model_dump())
    
    process_secure_file.delay(object_key, user.username, encrypt_manual)

    return {"filename": file.filename, "status": "File accepted for secure processing."}

@router.get("/list-secure")
async def list_secure_files(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection)
):
    """
    Lists file metadata from the secure_files collection in MongoDB.
    """
    user_files = files_db.find({"owner_username": user.username})

    files_list = []
    for file in user_files:
        files_list.append({
            "filename": file.get("filename"),
            "upload_date": file.get("upload_date"),
            "size_bytes": file.get("size_bytes"),
            "is_sensitive": file.get("is_sensitive"),
            "is_encrypted": file.get("is_encrypted", False)
        })
    return files_list

# --- FIX: ADD THIS MISSING DOWNLOAD ENDPOINT ---
@router.get("/download/{filename}")
async def generate_secure_download_url(
    filename: str, 
    user: UserInDB = Depends(require_2fa)
):
    """
    Generates a pre-signed URL for securely downloading a file.
    """
    object_key = f"{user.username}/{filename}"
    try:
        url = s3_client_primary.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.SECURE_S3_BUCKET_NAME, 'Key': object_key},
            ExpiresIn=3600  # URL is valid for 1 hour
        )
        # The key "presigned_url" matches what the frontend expects
        return {"presigned_url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Could not generate download URL: {e}"
        )

@router.delete("/delete/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secure_file(
    filename: str, 
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection)
):
    """
    Deletes a file from both primary and replica S3 buckets and from MongoDB.
    """
    object_key = f"{user.username}/{filename}"
    try:
        s3_client_primary.delete_object(Bucket=settings.SECURE_S3_BUCKET_NAME, Key=object_key)
        s3_client_replica.delete_object(Bucket=settings.REPLICA_S3_BUCKET_NAME, Key=object_key)
        files_db.delete_one({"s3_key": object_key})
        return
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete file: {e}")

