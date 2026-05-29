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
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from pymongo.collection import Collection

from app.utils.config import settings
from app.auth.auth_utils import require_2fa
from app.users.user_model import UserInDB
from app.database.mongo_client import mongodb_client
from app.storage.models_storage import FileMetadata
from app.storage.manager import list_objects_aws
from app.storage.tasks import apply_encryption_to_file
from app.storage.cloud_credentials import (
    SecureAwsStorage,
    delete_secure_object_dual,
    put_secure_object_dual,
    resolve_secure_aws_storage,
)
from app.security.encryption_handler import (
    decrypt_file_client_side,
    extract_encrypted_file_components,
)
from app.security.sensitive_file_detector import scan_file_content

# The prefix is removed here as it is handled in main.py
router = APIRouter(tags=["Security"])


def get_secure_files_collection() -> Collection:
    return mongodb_client.get_collection("secure_files")


def _persist_sse_secure_file(
    files_db: Collection,
    *,
    filename: str,
    owner_username: str,
    file_content: bytes,
    is_sensitive: bool,
    storage: SecureAwsStorage,
    scan_reasons: Optional[list] = None,
) -> dict:
    """Upload bytes to secure vault (BYOC bucket or platform dual buckets) with SSE-S3."""
    object_key = storage.object_key(owner_username, filename)
    put_secure_object_dual(
        storage, object_key, file_content, server_side_encryption=True
    )
    file_metadata = FileMetadata(
        filename=filename,
        s3_key=object_key,
        owner_username=owner_username,
        size_bytes=len(file_content),
        is_sensitive=is_sensitive,
        is_encrypted=True,
        encryption_method="server-side",
        encryption_status="encrypted",
        client_side_encrypted=False,
    )
    doc = file_metadata.model_dump()
    doc["upload_date"] = datetime.utcnow()
    doc["cloud_bucket"] = storage.primary_bucket
    doc["is_byoc"] = storage.is_byoc
    if scan_reasons is not None:
        doc["scan_reasons"] = scan_reasons
    files_db.update_one(
        {"filename": filename, "owner_username": owner_username},
        {"$set": doc, "$unset": {"temp_file_content": "", "awaiting_encryption_choice": ""}},
        upsert=True,
    )
    return {
        "filename": filename,
        "needs_encryption": False,
        "status": "auto_encrypted_sse",
        "encryption_method": "server-side",
        "is_sensitive": is_sensitive,
        "message": "Sensitive data detected — file protected automatically with SSE-S3 (primary + replica).",
    }


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
    removed: int
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
        storage = resolve_secure_aws_storage(user.username)
        bucket_name = storage.primary_bucket
        user_prefix = storage.list_prefix
        objects = list_objects_aws(
            bucket_name=bucket_name,
            prefix=user_prefix,
            access_key_id=storage.access_key_id,
            secret_access_key=storage.secret_access_key,
            session_token=storage.session_token,
            region_name=storage.region,
        )

        inserted = 0
        already_present = 0
        skipped_non_user_prefix = 0

        # Collect all valid S3 object keys so we can detect stale DB records
        live_s3_keys: set[str] = set()

        for obj in objects:
            object_key = obj.get("object_key") or ""
            if not object_key.startswith(user_prefix):
                skipped_non_user_prefix += 1
                continue

            filename = object_key[len(user_prefix) :]
            if not filename or filename.endswith("/"):
                continue

            live_s3_keys.add(object_key)

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
                head = storage.primary_client.head_object(
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
                "cloud_bucket": bucket_name,
                "is_byoc": storage.is_byoc,
                "is_sensitive": False,
                **encryption_flags,
            }
            files_db.insert_one(doc)
            inserted += 1

        # --- Remove stale DB records for files no longer present in S3 ---
        removed = 0
        import re

        prefix_base = re.escape(user_prefix.rstrip("/"))
        stale_filter = {
            "owner_username": user.username,
            "s3_key": {"$regex": f"^{prefix_base}/"},
        }
        if live_s3_keys:
            stale_filter["s3_key"] = {
                "$regex": f"^{prefix_base}/",
                "$nin": list(live_s3_keys),
            }
        stale_cursor = files_db.find(stale_filter, {"_id": 1, "filename": 1})
        stale_ids = [doc["_id"] for doc in stale_cursor]
        if stale_ids:
            from app.utils.logger import setup_logger
            _logger = setup_logger(__name__)
            result = files_db.delete_many({"_id": {"$in": stale_ids}})
            removed = result.deleted_count
            _logger.info(f"Secure sync removed {removed} stale record(s) for user {user.username}")

        return SecureSyncResponse(
            inserted=inserted,
            already_present=already_present,
            removed=removed,
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
    always_ask_encryption: bool = Form(False),
    file: UploadFile = File(...)
):
    """
    Step 1: Scan file for sensitive data BEFORE uploading to S3.
    Sensitive files auto-encrypt with SSE-S3 unless user forces manual encryption choice.
    """
    file_content = await file.read()
    file_size = len(file_content)
    storage = resolve_secure_aws_storage(user.username)

    scan = scan_file_content(file_content, file.filename)
    is_sensitive = scan.is_sensitive

    if is_sensitive and not encrypt_manual and not always_ask_encryption:
        try:
            return _persist_sse_secure_file(
                files_db,
                filename=file.filename,
                owner_username=user.username,
                file_content=file_content,
                is_sensitive=True,
                storage=storage,
                scan_reasons=scan.reasons,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Auto SSE-S3 upload failed: {str(e)}",
            ) from e

    needs_encryption = is_sensitive or encrypt_manual

    if needs_encryption:
        # Store file temporarily in database (not S3 yet) and ask user for encryption choice
        temp_file_doc = {
            "filename": file.filename,
            "owner_username": user.username,
            "size_bytes": file_size,
            "is_sensitive": is_sensitive,
            "scan_reasons": scan.reasons,
            "awaiting_encryption_choice": True,
            "encryption_status": "awaiting_choice",
            "temp_file_content": file_content,
            "upload_date": datetime.utcnow(),
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
            "scan_reasons": scan.reasons,
            "status": "awaiting_encryption_choice",
        }
    else:
        try:
            return _persist_sse_secure_file(
                files_db,
                filename=file.filename,
                owner_username=user.username,
                file_content=file_content,
                is_sensitive=False,
                storage=storage,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}",
            ) from e


@router.post("/upload-client-encrypted", status_code=status.HTTP_200_OK)
async def upload_client_encrypted(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    file: UploadFile = File(...),
    original_filename: str = Form(...),
    is_sensitive: bool = Form(False),
):
    """
    Accept ciphertext from browser (zero-knowledge). Password never sent to API.
    Format: [salt][iv][AES-256-CBC ciphertext] — same as encryption_handler storage layout.
    """
    encrypted_body = await file.read()
    if len(encrypted_body) < 33:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload.")

    storage = resolve_secure_aws_storage(user.username)
    object_key = storage.object_key(user.username, original_filename)
    try:
        put_secure_object_dual(
            storage,
            object_key,
            encrypted_body,
            metadata={"encryption": "client-side", "algorithm": "AES-256-CBC"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store encrypted file: {str(e)}",
        )

    doc = {
        "filename": original_filename,
        "s3_key": object_key,
        "owner_username": user.username,
        "size_bytes": len(encrypted_body),
        "upload_date": datetime.utcnow(),
        "cloud_bucket": storage.primary_bucket,
        "is_byoc": storage.is_byoc,
        "is_sensitive": is_sensitive,
        "is_encrypted": True,
        "encryption_method": "client-side",
        "encryption_status": "encrypted",
        "client_side_encrypted": True,
        "awaiting_encryption_choice": False,
    }
    files_db.update_one(
        {"filename": original_filename, "owner_username": user.username},
        {"$set": doc, "$unset": {"temp_file_content": "", "scan_reasons": ""}},
        upsert=True,
    )
    return {
        "filename": original_filename,
        "encryption_method": "client-side",
        "client_side_encrypted": True,
        "message": "Encrypted file stored in secure vault.",
    }

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
            "client_side_encrypted": file.get("client_side_encrypted", False),
            "scan_reasons": file.get("scan_reasons", []),
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
    
    if request.encryption_method != "server-side":
        raise HTTPException(
            status_code=400,
            detail="Client-side encryption must be performed in the browser. Use upload-client-encrypted.",
        )

    # Get the temp file content
    file_content = file_doc.get("temp_file_content")
    if not file_content:
        raise HTTPException(status_code=400, detail="Temporary file content not found")
    
    storage = resolve_secure_aws_storage(user.username)
    try:
        result = _persist_sse_secure_file(
            files_db,
            filename=request.filename,
            owner_username=user.username,
            file_content=file_content,
            is_sensitive=bool(file_doc.get("is_sensitive")),
            storage=storage,
            scan_reasons=file_doc.get("scan_reasons"),
        )
        return {
            "message": "Server-side encryption (SSE-S3) applied successfully",
            "filename": request.filename,
            "encryption_method": "server-side",
            "status": result.get("status", "uploaded"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}") from e


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
    storage = resolve_secure_aws_storage(user.username)
    object_key = storage.object_key(user.username, filename)
    file_doc = files_db.find_one(
        {"owner_username": user.username, "$or": [{"s3_key": object_key}, {"filename": filename}]}
    )
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    object_key = file_doc.get("s3_key") or object_key
    bucket = file_doc.get("cloud_bucket") or storage.primary_bucket

    # Check if file is client-side encrypted
    if file_doc.get("client_side_encrypted"):
        return {
            "client_side_encrypted": True,
            "message": "Decrypt in your browser with your encryption password.",
            "encryption_method": "client-side",
        }
    
    try:
        url = storage.primary_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': object_key},
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


@router.get("/download-ciphertext/{filename}")
async def download_client_encrypted_ciphertext(
    filename: str,
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
):
    """Return raw ciphertext for browser-side decryption (zero-knowledge)."""
    storage = resolve_secure_aws_storage(user.username)
    object_key = storage.object_key(user.username, filename)
    file_doc = files_db.find_one(
        {"owner_username": user.username, "$or": [{"s3_key": object_key}, {"filename": filename}]}
    )
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    object_key = file_doc.get("s3_key") or object_key
    bucket = file_doc.get("cloud_bucket") or storage.primary_bucket
    if not file_doc.get("client_side_encrypted"):
        raise HTTPException(
            status_code=400,
            detail="File is not browser-encrypted. Use the standard download URL.",
        )
    try:
        response = storage.primary_client.get_object(Bucket=bucket, Key=object_key)
        body = response["Body"].read()
        return Response(
            content=body,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.encrypted"',
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not download ciphertext: {e}")


@router.post("/decrypt-download")
async def decrypt_and_download(
    request: DecryptionRequest,
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection)
):
    """
    Decrypts a client-side encrypted file with user's password and returns the file directly.
    """
    storage = resolve_secure_aws_storage(user.username)
    object_key = storage.object_key(user.username, request.filename)
    file_doc = files_db.find_one(
        {
            "owner_username": user.username,
            "$or": [{"s3_key": object_key}, {"filename": request.filename}],
        }
    )
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    object_key = file_doc.get("s3_key") or object_key
    bucket = file_doc.get("cloud_bucket") or storage.primary_bucket

    if not file_doc.get("client_side_encrypted"):
        raise HTTPException(status_code=400, detail="File is not client-side encrypted")
    
    try:
        response = storage.primary_client.get_object(Bucket=bucket, Key=object_key)
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
    storage = resolve_secure_aws_storage(user.username)
    object_key = storage.object_key(user.username, filename)
    file_doc = files_db.find_one(
        {"owner_username": user.username, "$or": [{"s3_key": object_key}, {"filename": filename}]}
    )
    if file_doc:
        object_key = file_doc.get("s3_key") or object_key
    try:
        delete_secure_object_dual(storage, object_key)
        files_db.delete_one({"owner_username": user.username, "s3_key": object_key})
        return
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete file: {e}")

