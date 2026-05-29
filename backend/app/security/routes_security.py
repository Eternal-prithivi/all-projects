# =============================================================================
# MODULE: routes_security.py  (449 lines)
# PURPOSE: 2FA-gated secure file vault — upload (with sensitive scan + encryption
#          choice flow), list, download (presigned or decrypt), delete
# READS FROM:  secure_files collection, AWS S3 (SECURE_S3_BUCKET + REPLICA)
# WRITES TO:   secure_files collection, AWS S3 (SECURE_S3_BUCKET + REPLICA)
# DEPENDS ON:  auth_utils.require_2fa() (NOT get_current_user — 2FA required)
#              encryption_handler.py (AES-256 client-side), boto3 (SSE server-side)
# MOUNTED AT:  /api/security → upload-secure, list-secure, choose-encryption,
#              download/{filename}, decrypt-download, delete/{filename}, sync/aws
# DO NOT:
#   - Swap require_2fa() for get_current_user() — this vault needs 2FA verified
#   - Change the two-step upload flow (scan → await choice → encrypt → S3)
#   - Use the same S3 bucket as regular storage (SECURE_S3_BUCKET_NAME is separate)
# =============================================================================
import boto3
import re
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from pymongo.collection import Collection
from botocore.config import Config

from app.utils.config import settings
from app.auth.auth_utils import require_2fa
from app.users.user_model import UserInDB
from app.database.mongo_client import mongodb_client
from app.storage.models_storage import FileMetadata
from app.storage.manager import list_objects_aws
from app.storage.tasks import apply_encryption_to_file
from app.security.encryption_handler import (
    decrypt_file_client_side,
    extract_encrypted_file_components
)

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


# Request models
class EncryptionChoiceRequest(BaseModel):
    filename: str
    encryption_method: str  # "server-side" or "client-side"
    password: Optional[str] = None  # Required for client-side


class DecryptionRequest(BaseModel):
    filename: str
    password: str  # User's password for decryption


class SecureSyncResponse(BaseModel):
    inserted: int
    already_present: int
    skipped_non_user_prefix: int
    total_objects_seen: int
    bucket_name: str
    scanned_prefix: str


def _encryption_flags_from_s3_head(head: dict) -> dict:
    """Infer secure-file encryption metadata from S3 object headers."""
    metadata = head.get("Metadata") or {}
    if metadata.get("encryption") == "client-side":
        return {
            "is_encrypted": True,
            "encryption_method": "client-side",
            "encryption_status": "encrypted",
            "client_side_encrypted": True,
            "awaiting_encryption_choice": False,
        }
    if head.get("ServerSideEncryption"):
        return {
            "is_encrypted": True,
            "encryption_method": "server-side",
            "encryption_status": "encrypted",
            "client_side_encrypted": False,
            "awaiting_encryption_choice": False,
        }
    return {
        "is_encrypted": False,
        "encryption_method": "none",
        "encryption_status": "none",
        "client_side_encrypted": False,
        "awaiting_encryption_choice": False,
    }


@router.post("/sync/aws", response_model=SecureSyncResponse)
async def sync_secure_aws_bucket(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
):
    """
    On-demand reconcile of the secure S3 vault into MongoDB (free-tier friendly).

    Scans SECURE_S3_BUCKET_NAME under the user's prefix only. Does not delete DB
    records or modify S3 objects. New rows inherit encryption flags from S3 headers.
    """
    try:
        bucket_name = settings.SECURE_S3_BUCKET_NAME
        user_prefix = f"{user.username}/"
        objects = list_objects_aws(
            bucket_name=bucket_name,
            prefix=user_prefix,
            access_key_id=settings.AWS_ACCESS_KEY_ID,
            secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.PRIMARY_S3_REGION,
        )

        inserted = 0
        already_present = 0
        skipped_non_user_prefix = 0

        for obj in objects:
            object_key = obj.get("object_key") or ""
            if not object_key.startswith(user_prefix):
                skipped_non_user_prefix += 1
                continue

            filename = object_key[len(user_prefix) :]
            if not filename or filename.endswith("/"):
                continue

            existing = files_db.find_one(
                {
                    "owner_username": user.username,
                    "$or": [{"s3_key": object_key}, {"filename": filename}],
                },
                {"_id": 1},
            )
            if existing:
                already_present += 1
                continue

            encryption_flags = {
                "is_encrypted": False,
                "encryption_method": "none",
                "encryption_status": "none",
                "client_side_encrypted": False,
                "awaiting_encryption_choice": False,
            }
            try:
                head = s3_client_primary.head_object(
                    Bucket=bucket_name, Key=object_key
                )
                encryption_flags = _encryption_flags_from_s3_head(head)
            except Exception:
                pass

            upload_date = obj.get("last_modified") or datetime.utcnow()
            doc = {
                "filename": filename,
                "s3_key": object_key,
                "owner_username": user.username,
                "size_bytes": int(obj.get("size_bytes", 0) or 0),
                "upload_date": upload_date,
                "is_sensitive": False,
                **encryption_flags,
            }
            files_db.insert_one(doc)
            inserted += 1

        return SecureSyncResponse(
            inserted=inserted,
            already_present=already_present,
            skipped_non_user_prefix=skipped_non_user_prefix,
            total_objects_seen=len(objects),
            bucket_name=bucket_name,
            scanned_prefix=user_prefix,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync secure AWS bucket: {str(e)}",
        )


@router.post("/upload-secure", status_code=status.HTTP_200_OK)
async def upload_secure_file(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    encrypt_manual: bool = Form(False),
    file: UploadFile = File(...)
):
    """
    Step 1: Scan file for sensitive data BEFORE uploading to S3.
    If encryption needed, return immediately asking user to choose encryption method.
    """
    import re
    import io
    
    # Read file content for scanning
    file_content = await file.read()
    file_size = len(file_content)
    
    # Scan for sensitive data
    is_sensitive = False
    try:
        content_str = file_content.decode('utf-8', errors='ignore')
        credit_card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
        secret_keywords_pattern = r'(?i)\b(password|secret|key|pwd|token|credentials|apikeys|private_key|auth_token)\b'
        
        if re.search(credit_card_pattern, content_str) or re.search(secret_keywords_pattern, content_str):
            is_sensitive = True
    except:
        pass
    
    # Determine if encryption is needed
    needs_encryption = is_sensitive or encrypt_manual
    
    if needs_encryption:
        # Store file temporarily in database (not S3 yet) and ask user for encryption choice
        temp_file_doc = {
            "filename": file.filename,
            "owner_username": user.username,
            "size_bytes": file_size,
            "is_sensitive": is_sensitive,
            "awaiting_encryption_choice": True,
            "encryption_status": "awaiting_choice",
            "temp_file_content": file_content,  # Store temporarily
            "upload_date": datetime.utcnow()
        }
        
        # Check if file already exists
        existing = files_db.find_one({"filename": file.filename, "owner_username": user.username})
        if existing:
            files_db.update_one(
                {"filename": file.filename, "owner_username": user.username},
                {"$set": temp_file_doc}
            )
        else:
            files_db.insert_one(temp_file_doc)
        
        return {
            "filename": file.filename,
            "needs_encryption": True,
            "is_sensitive": is_sensitive,
            "status": "awaiting_encryption_choice"
        }
    else:
        # File doesn't need encryption, upload directly to S3
        object_key = f"{user.username}/{file.filename}"
        try:
            s3_client_primary.upload_fileobj(
                io.BytesIO(file_content),
                settings.SECURE_S3_BUCKET_NAME,
                object_key
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )
        
        file_metadata = FileMetadata(
            filename=file.filename,
            s3_key=object_key,
            owner_username=user.username,
            size_bytes=file_size,
            is_sensitive=False,
            is_encrypted=False,
            encryption_status="none"
        )
        files_db.insert_one(file_metadata.model_dump())
        
        return {"filename": file.filename, "needs_encryption": False, "status": "uploaded"}

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
            "is_encrypted": file.get("is_encrypted", False),
            "encryption_method": file.get("encryption_method", "none"),
            "encryption_status": file.get("encryption_status", "none"),
            "awaiting_encryption_choice": file.get("awaiting_encryption_choice", False),
            "client_side_encrypted": file.get("client_side_encrypted", False)
        })
    return files_list


@router.post("/choose-encryption")
async def choose_encryption_method(
    request: EncryptionChoiceRequest,
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection)
):
    """
    Step 2: User selects encryption method.
    Apply encryption to temp file, then upload encrypted file to S3.
    """
    import io
    from app.security.encryption_handler import encrypt_file_client_side, prepare_encrypted_file_for_storage
    from app.utils.logger import setup_logger
    
    logger = setup_logger(__name__)
    logger.info(f"Encryption choice request: filename={request.filename}, method={request.encryption_method}, has_password={bool(request.password)}")
    
    # Find the temporary file
    file_doc = files_db.find_one({"filename": request.filename, "owner_username": user.username})
    if not file_doc:
        logger.error(f"File not found: {request.filename} for user {user.username}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"File doc found: awaiting_choice={file_doc.get('awaiting_encryption_choice')}, has_temp_content={bool(file_doc.get('temp_file_content'))}")
    
    if not file_doc.get("awaiting_encryption_choice"):
        raise HTTPException(status_code=400, detail="File is not awaiting encryption choice")
    
    # Validate encryption method
    if request.encryption_method not in ["server-side", "client-side"]:
        raise HTTPException(status_code=400, detail="Invalid encryption method")
    
    # Validate password for client-side encryption
    if request.encryption_method == "client-side" and not request.password:
        raise HTTPException(status_code=400, detail="Password required for client-side encryption")
    
    # Get the temp file content
    file_content = file_doc.get("temp_file_content")
    if not file_content:
        raise HTTPException(status_code=400, detail="Temporary file content not found")
    
    object_key = f"{user.username}/{request.filename}"
    
    try:
        if request.encryption_method == "server-side":
            # Upload with AWS server-side encryption
            s3_client_primary.put_object(
                Bucket=settings.SECURE_S3_BUCKET_NAME,
                Key=object_key,
                Body=file_content,
                ServerSideEncryption='AES256'
            )
            
            # Replicate to backup
            s3_client_replica.put_object(
                Bucket=settings.REPLICA_S3_BUCKET_NAME,
                Key=object_key,
                Body=file_content,
                ServerSideEncryption='AES256'
            )
            
            # Update database
            files_db.update_one(
                {"filename": request.filename, "owner_username": user.username},
                {
                    "$set": {
                        "s3_key": object_key,
                        "is_encrypted": True,
                        "encryption_method": "server-side",
                        "encryption_status": "encrypted",
                        "awaiting_encryption_choice": False,
                        "client_side_encrypted": False
                    },
                    "$unset": {"temp_file_content": ""}  # Remove temp data
                }
            )
            
        else:  # client-side encryption
            # Encrypt file with user's password
            encrypted_content, salt, iv = encrypt_file_client_side(file_content, request.password)
            final_encrypted_data = prepare_encrypted_file_for_storage(encrypted_content, salt, iv)
            
            # Upload encrypted file to S3
            s3_client_primary.put_object(
                Bucket=settings.SECURE_S3_BUCKET_NAME,
                Key=object_key,
                Body=final_encrypted_data,
                Metadata={
                    'encryption': 'client-side',
                    'algorithm': 'AES-256-CBC'
                }
            )
            
            # Replicate to backup
            s3_client_replica.put_object(
                Bucket=settings.REPLICA_S3_BUCKET_NAME,
                Key=object_key,
                Body=final_encrypted_data,
                Metadata={
                    'encryption': 'client-side',
                    'algorithm': 'AES-256-CBC'
                }
            )
            
            # Update database
            files_db.update_one(
                {"filename": request.filename, "owner_username": user.username},
                {
                    "$set": {
                        "s3_key": object_key,
                        "is_encrypted": True,
                        "encryption_method": "client-side",
                        "encryption_status": "encrypted",
                        "awaiting_encryption_choice": False,
                        "client_side_encrypted": True
                    },
                    "$unset": {"temp_file_content": ""}  # Remove temp data
                }
            )
        
        return {
            "message": f"{request.encryption_method} encryption applied successfully",
            "filename": request.filename,
            "encryption_method": request.encryption_method
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")


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
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection)
):
    """
    Generates a pre-signed URL for securely downloading a file.
    For client-side encrypted files, returns metadata indicating password is needed.
    """
    object_key = f"{user.username}/{filename}"
    
    # Get file metadata
    file_doc = files_db.find_one({"s3_key": object_key, "owner_username": user.username})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if file is client-side encrypted
    if file_doc.get("client_side_encrypted"):
        return {
            "client_side_encrypted": True,
            "message": "This file is encrypted with your password. Use the decryption endpoint.",
            "encryption_method": "client-side"
        }
    
    try:
        url = s3_client_primary.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.SECURE_S3_BUCKET_NAME, 'Key': object_key},
            ExpiresIn=3600  # URL is valid for 1 hour
        )
        # The key "presigned_url" matches what the frontend expects
        return {
            "presigned_url": url,
            "client_side_encrypted": False,
            "encryption_method": file_doc.get("encryption_method", "none")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Could not generate download URL: {e}"
        )


@router.post("/decrypt-download")
async def decrypt_and_download(
    request: DecryptionRequest,
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection)
):
    """
    Decrypts a client-side encrypted file with user's password and returns the file directly.
    """
    object_key = f"{user.username}/{request.filename}"
    
    # Get file metadata
    file_doc = files_db.find_one({"s3_key": object_key, "owner_username": user.username})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_doc.get("client_side_encrypted"):
        raise HTTPException(status_code=400, detail="File is not client-side encrypted")
    
    try:
        # Download encrypted file from S3
        response = s3_client_primary.get_object(
            Bucket=settings.SECURE_S3_BUCKET_NAME,
            Key=object_key
        )
        encrypted_content = response['Body'].read()
        salt, iv, encrypted_data = extract_encrypted_file_components(encrypted_content)
        
        # Decrypt the file
        try:
            decrypted_content = decrypt_file_client_side(
                encrypted_data,
                request.password,
                salt,
                iv
            )
        except Exception as decrypt_error:
            raise HTTPException(
                status_code=401,
                detail="Incorrect password or corrupted file"
            )
        
        # Return decrypted file as download using Response
        return Response(
            content=decrypted_content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{request.filename}"',
                "Content-Length": str(len(decrypted_content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decryption failed: {str(e)}"
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

