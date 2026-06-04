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
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
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
from app.byoc.aws_bucket_discovery import classify_bucket_role
from app.byoc.aws_bucket_helpers import REPLICA_REGION_DEFAULT
from app.byoc.credential_resolver import get_aws_bucket_layout
from app.cloud.availability import CloudFeature, assert_provider_available
from app.cloud.providers import normalize_provider
from app.storage.cloud_credentials import (
    SecureAwsStorage,
    build_aws_s3_client_for_bucket,
    resolve_secure_aws_storage,
)
from app.storage.secure_vault import (
    delete_secure_vault_object,
    download_secure_vault_bytes,
    presigned_secure_download_url,
    put_secure_vault_object,
    resolve_secure_storage,
    secure_replication_requested,
    vault_csp,
)
from app.storage.manager import list_objects_azure, list_objects_gcp
from app.storage.file_queries import (
    build_secure_list_filter,
    find_secure_file,
)
from app.security.encryption_handler import (
    decrypt_file_client_side,
    extract_encrypted_file_components,
)
from app.security.sensitive_file_detector import scan_file_content

# The prefix is removed here as it is handled in main.py
router = APIRouter(tags=["Security"])


class SecureSyncResponse(BaseModel):
    inserted: int
    already_present: int
    removed: int
    skipped_non_user_prefix: int
    total_objects_seen: int
    bucket_name: str
    scanned_prefix: str


def get_secure_files_collection() -> Collection:
    return mongodb_client.get_collection("secure_files")


def _resolve_secure_bucket_sync(
    username: str,
    bucket: Optional[str],
    region: Optional[str],
) -> Tuple[Any, str, str, str, SecureAwsStorage]:
    """Return (s3_client, bucket_name, list_prefix, region, storage_ctx)."""
    storage = resolve_secure_aws_storage(username)
    bucket_name = bucket or storage.primary_bucket
    layout = get_aws_bucket_layout(username)

    if layout and bucket_name == layout.get("replica_bucket_name"):
        sync_region = layout.get("replica_region") or REPLICA_REGION_DEFAULT
        client, _ = build_aws_s3_client_for_bucket(username, sync_region)
        return client, bucket_name, storage.list_prefix, sync_region, storage

    if bucket_name == storage.primary_bucket:
        return storage.primary_client, bucket_name, storage.list_prefix, storage.region, storage

    sync_region = region or storage.region
    if layout and bucket_name:
        role = classify_bucket_role(bucket_name, layout)
        if role == "storage":
            raise HTTPException(
                status_code=400,
                detail="Use the Storage page to sync general storage buckets.",
            )
        if bucket_name == layout.get("secure_bucket_name"):
            sync_region = layout.get("primary_region") or sync_region

    client, _ = build_aws_s3_client_for_bucket(username, sync_region)
    scanned_prefix = "" if storage.is_byoc else storage.list_prefix
    return client, bucket_name, scanned_prefix, sync_region, storage


def _persist_sse_secure_file(
    files_db: Collection,
    *,
    filename: str,
    owner_username: str,
    file_content: bytes,
    is_sensitive: bool,
    storage,
    scan_reasons: Optional[list] = None,
    enable_replication: bool = False,
    replica_region: Optional[str] = None,
) -> dict:
    """Upload bytes to secure vault with provider-managed encryption at rest."""
    object_key = storage.object_key(owner_username, filename)
    replicate = secure_replication_requested(storage, enable_replication)
    put_secure_vault_object(
        storage,
        object_key,
        file_content,
        server_side_encryption=True,
        replicate=replicate,
    )
    csp = vault_csp(storage)
    encrypt_msg = (
        "Sensitive data detected — file protected automatically with SSE-S3 (primary + replica)."
        if csp == "AWS"
        else f"Sensitive data detected — file protected with {csp} server-side encryption."
    )
    file_metadata = FileMetadata(
        filename=filename,
        s3_key=object_key,
        owner_username=owner_username,
        size_bytes=len(file_content),
        csp=csp,
        is_sensitive=is_sensitive,
        is_encrypted=True,
        encryption_method="server-side",
        encryption_status="encrypted",
        client_side_encrypted=False,
    )
    doc = file_metadata.model_dump()
    doc["upload_date"] = datetime.utcnow()
    doc["cloud_bucket"] = storage.primary_bucket
    doc["region"] = getattr(storage, "region", None) or ""
    doc["is_byoc"] = storage.is_byoc
    if scan_reasons is not None:
        doc["scan_reasons"] = scan_reasons
    doc["replication_enabled"] = replicate
    if replica_region:
        doc["replica_region"] = replica_region
    doc.pop("awaiting_encryption_choice", None)
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
        "message": encrypt_msg,
    }


def _sync_secure_objects(
    user: UserInDB,
    files_db: Collection,
    csp: str,
    *,
    bucket: Optional[str] = None,
    region: Optional[str] = None,
) -> SecureSyncResponse:
    """Reconcile secure vault objects into MongoDB for AWS, GCP, or Azure."""
    provider = normalize_provider(csp)
    assert_provider_available(user.username, provider, CloudFeature.SECURITY)
    if provider == "AWS":
        sync_client, bucket_name, user_prefix, sync_region, storage = _resolve_secure_bucket_sync(
            user.username, bucket, region
        )
        objects = list_objects_aws(
            bucket_name=bucket_name,
            prefix=user_prefix,
            access_key_id=storage.access_key_id,
            secret_access_key=storage.secret_access_key,
            session_token=storage.session_token,
            region_name=sync_region,
        )
        encryption_from_head = _encryption_flags_from_s3_head
        head_client = sync_client
        head_bucket = bucket_name
    elif provider == "GCP":
        storage = resolve_secure_storage(user.username, "GCP")
        bucket_name = bucket or storage.bucket_name
        scan_prefix = "" if storage.is_byoc else storage.list_prefix
        user_prefix = storage.list_prefix
        objects = list_objects_gcp(
            username=user.username,
            bucket_name=bucket_name,
            prefix=scan_prefix,
        )
        encryption_from_head = None
        head_client = None
        head_bucket = bucket_name
        sync_region = ""
    else:
        storage = resolve_secure_storage(user.username, "Azure")
        bucket_name = bucket or storage.container_name
        scan_prefix = "" if storage.is_byoc else storage.list_prefix
        user_prefix = storage.list_prefix
        objects = list_objects_azure(
            username=user.username,
            container_name=bucket_name,
            prefix=scan_prefix,
        )
        encryption_from_head = None
        head_client = None
        head_bucket = bucket_name
        sync_region = ""

    inserted = 0
    already_present = 0
    skipped_non_user_prefix = 0
    live_keys: set[str] = set()
    vault_csp_value = vault_csp(storage) if provider != "AWS" else "AWS"

    for obj in objects:
        object_key = obj.get("object_key") or ""
        if user_prefix and not object_key.startswith(user_prefix):
            skipped_non_user_prefix += 1
            continue
        filename = (
            object_key[len(user_prefix):]
            if user_prefix and object_key.startswith(user_prefix)
            else object_key
        )
        if not filename or filename.endswith("/"):
            continue
        live_keys.add(object_key)
        existing = files_db.find_one(
            {
                "owner_username": user.username,
                "cloud_bucket": bucket_name,
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
        if encryption_from_head and head_client:
            try:
                head = head_client.head_object(Bucket=head_bucket, Key=object_key)
                encryption_flags = encryption_from_head(head)
            except Exception:
                pass
        doc = {
            "filename": filename,
            "s3_key": object_key,
            "owner_username": user.username,
            "size_bytes": int(obj.get("size_bytes", 0) or 0),
            "upload_date": obj.get("last_modified") or datetime.utcnow(),
            "cloud_bucket": bucket_name,
            "region": sync_region or None,
            "csp": vault_csp_value,
            "is_byoc": storage.is_byoc,
            "is_sensitive": False,
            **encryption_flags,
        }
        files_db.insert_one(doc)
        inserted += 1

    removed = 0
    if provider == "AWS":
        primary_secure = storage.primary_bucket
        if bucket_name == primary_secure:
            stale_filter = {
                "owner_username": user.username,
                "$or": [
                    {"cloud_bucket": bucket_name},
                    {"cloud_bucket": {"$exists": False}},
                    {"cloud_bucket": None},
                    {"cloud_bucket": ""},
                ],
            }
        else:
            stale_filter = {
                "owner_username": user.username,
                "cloud_bucket": bucket_name,
            }
    else:
        stale_filter = {
            "owner_username": user.username,
            "csp": vault_csp_value,
            "cloud_bucket": bucket_name,
        }
    if live_keys:
        stale_filter["s3_key"] = {"$nin": list(live_keys)}
    stale_ids = [doc["_id"] for doc in files_db.find(stale_filter, {"_id": 1})]
    if stale_ids:
        removed = files_db.delete_many({"_id": {"$in": stale_ids}}).deleted_count

    return SecureSyncResponse(
        inserted=inserted,
        already_present=already_present,
        removed=removed,
        skipped_non_user_prefix=skipped_non_user_prefix,
        total_objects_seen=len(objects),
        bucket_name=bucket_name,
        scanned_prefix=user_prefix,
    )


# Request models
class EncryptionChoiceRequest(BaseModel):
    filename: str
    encryption_method: str  # "server-side" or "client-side"
    password: Optional[str] = None  # Required for client-side
    csp: Optional[str] = None
    enable_replication: bool = False
    replica_region: Optional[str] = None


class DecryptionRequest(BaseModel):
    filename: str
    password: str  # User's password for decryption


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


@router.post("/sync/{csp}", response_model=SecureSyncResponse)
async def sync_secure_vault(
    csp: str,
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """Reconcile secure vault for AWS, GCP, or Azure into MongoDB."""
    try:
        return _sync_secure_objects(
            user, files_db, csp, bucket=bucket, region=region
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync secure {csp} vault: {str(e)}",
        )


@router.post("/sync/aws", response_model=SecureSyncResponse)
async def sync_secure_aws_bucket(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """Backward-compatible alias for POST /sync/AWS."""
    return await sync_secure_vault("AWS", user, files_db, bucket, region)


@router.post("/sync/gcp", response_model=SecureSyncResponse)
async def sync_secure_gcp_bucket(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
):
    return await sync_secure_vault("GCP", user, files_db, bucket=bucket)


@router.post("/sync/azure", response_model=SecureSyncResponse)
async def sync_secure_azure_container(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    container: Optional[str] = Query(None),
):
    return await sync_secure_vault("Azure", user, files_db, bucket=container)


@router.post("/scan", status_code=status.HTTP_200_OK)
async def scan_secure_file(
    user: UserInDB = Depends(require_2fa),
    file: UploadFile = File(...),
):
    """Scan file for sensitive content before vault upload (no storage)."""
    file_content = await file.read()
    scan = scan_file_content(file_content, file.filename)
    return {
        "filename": file.filename,
        "is_sensitive": scan.is_sensitive,
        "scan_reasons": scan.reasons,
        "size_bytes": len(file_content),
    }


@router.post("/upload-secure", status_code=status.HTTP_200_OK)
async def upload_secure_file(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    encrypt_manual: bool = Form(False),
    always_ask_encryption: bool = Form(False),
    csp: str = Form("AWS"),
    file: UploadFile = File(...),
):
    """
    Step 1: Scan file for sensitive data BEFORE uploading to S3.
    Sensitive files auto-encrypt with SSE-S3 unless user forces manual encryption choice.
    """
    file_content = await file.read()
    file_size = len(file_content)
    try:
        provider = normalize_provider(csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    assert_provider_available(user.username, provider, CloudFeature.SECURITY)
    storage = resolve_secure_storage(user.username, provider)

    scan = scan_file_content(file_content, file.filename)
    is_sensitive = scan.is_sensitive

    # Sensitive files always enter the encryption wizard (no silent auto-upload).
    needs_encryption = is_sensitive or encrypt_manual or always_ask_encryption

    if needs_encryption:
        # Store file temporarily in database (not S3 yet) and ask user for encryption choice
        temp_file_doc = {
            "filename": file.filename,
            "owner_username": user.username,
            "size_bytes": file_size,
            "csp": provider,
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
    csp: str = Form("AWS"),
    enable_replication: bool = Form(False),
):
    """
    Accept ciphertext from browser (zero-knowledge). Password never sent to API.
    Format: [salt][iv][AES-256-CBC ciphertext] — same as encryption_handler storage layout.
    """
    encrypted_body = await file.read()
    if len(encrypted_body) < 33:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload.")

    try:
        provider = normalize_provider(csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    assert_provider_available(user.username, provider, CloudFeature.SECURITY)
    storage = resolve_secure_storage(user.username, provider)
    object_key = storage.object_key(user.username, original_filename)
    replicate = secure_replication_requested(storage, enable_replication)
    try:
        put_secure_vault_object(
            storage,
            object_key,
            encrypted_body,
            metadata={"encryption": "client-side", "algorithm": "AES-256-CBC"},
            replicate=replicate,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store encrypted file: {str(e)}",
        ) from e

    doc = {
        "filename": original_filename,
        "s3_key": object_key,
        "owner_username": user.username,
        "size_bytes": len(encrypted_body),
        "upload_date": datetime.utcnow(),
        "cloud_bucket": storage.primary_bucket,
        "csp": provider,
        "is_byoc": storage.is_byoc,
        "is_sensitive": is_sensitive,
        "is_encrypted": True,
        "encryption_method": "client-side",
        "encryption_status": "encrypted",
        "client_side_encrypted": True,
        "awaiting_encryption_choice": False,
        "replication_enabled": replicate,
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
        "csp": provider,
        "replication_enabled": replicate,
        "message": f"Encrypted file stored in {provider} secure vault.",
    }

@router.get("/list-secure")
async def list_secure_files(
    user: UserInDB = Depends(require_2fa),
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """
    Lists file metadata from the secure_files collection in MongoDB.
    """
    query = build_secure_list_filter(user.username, bucket, region, None)
    files_list = []
    for file in files_db.find(query):
        file_csp = file.get("csp") or "AWS"
        files_list.append({
            "filename": file.get("filename"),
            "csp": file_csp,
            "upload_date": file.get("upload_date"),
            "size_bytes": file.get("size_bytes"),
            "is_sensitive": file.get("is_sensitive"),
            "is_encrypted": file.get("is_encrypted", False),
            "encryption_method": file.get("encryption_method", "none"),
            "encryption_status": file.get("encryption_status", "none"),
            "awaiting_encryption_choice": file.get("awaiting_encryption_choice", False),
            "client_side_encrypted": file.get("client_side_encrypted", False),
            "scan_reasons": file.get("scan_reasons", []),
            "cloud_bucket": file.get("cloud_bucket"),
            "region": file.get("region"),
            "s3_key": file.get("s3_key"),
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
    
    file_csp = request.csp or file_doc.get("csp") or "AWS"
    try:
        provider = normalize_provider(file_csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    assert_provider_available(user.username, provider, CloudFeature.SECURITY)
    storage = resolve_secure_storage(user.username, provider)
    try:
        result = _persist_sse_secure_file(
            files_db,
            filename=request.filename,
            owner_username=user.username,
            file_content=file_content,
            is_sensitive=bool(file_doc.get("is_sensitive")),
            storage=storage,
            scan_reasons=file_doc.get("scan_reasons"),
            enable_replication=request.enable_replication,
            replica_region=request.replica_region,
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
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
):
    """
    Generates a pre-signed URL for securely downloading a file.
    For client-side encrypted files, returns metadata indicating password is needed.
    """
    file_doc = find_secure_file(files_db, user.username, filename, bucket)
    file_csp = file_doc.get("csp") or "AWS"
    storage = resolve_secure_storage(user.username, file_csp)
    object_key = file_doc.get("s3_key") or storage.object_key(user.username, filename)
    target_bucket = file_doc.get("cloud_bucket") or storage.primary_bucket
    file_region = file_doc.get("region") or getattr(storage, "region", None)

    if file_doc.get("client_side_encrypted"):
        return {
            "client_side_encrypted": True,
            "message": "Decrypt in your browser with your encryption password.",
            "encryption_method": "client-side",
            "csp": file_csp,
        }

    try:
        url = presigned_secure_download_url(
            storage,
            object_key,
            user.username,
            bucket_override=target_bucket,
            region_override=file_region,
        )
        return {
            "presigned_url": url,
            "client_side_encrypted": False,
            "encryption_method": file_doc.get("encryption_method", "none"),
            "csp": file_csp,
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
    bucket: Optional[str] = Query(None),
):
    """Return raw ciphertext for browser-side decryption (zero-knowledge)."""
    file_doc = find_secure_file(files_db, user.username, filename, bucket)
    file_csp = file_doc.get("csp") or "AWS"
    storage = resolve_secure_storage(user.username, file_csp)
    object_key = file_doc.get("s3_key") or storage.object_key(user.username, filename)
    target_bucket = file_doc.get("cloud_bucket") or storage.primary_bucket
    if not file_doc.get("client_side_encrypted"):
        raise HTTPException(
            status_code=400,
            detail="File is not browser-encrypted. Use the standard download URL.",
        )
    try:
        body = download_secure_vault_bytes(
            storage,
            object_key,
            user.username,
            bucket_override=target_bucket,
            region_override=file_doc.get("region"),
        )
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
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
):
    """
    Decrypts a client-side encrypted file with user's password and returns the file directly.
    """
    file_doc = find_secure_file(files_db, user.username, request.filename, bucket)
    file_csp = file_doc.get("csp") or "AWS"
    storage = resolve_secure_storage(user.username, file_csp)
    object_key = file_doc.get("s3_key") or storage.object_key(
        user.username, request.filename
    )
    target_bucket = file_doc.get("cloud_bucket") or storage.primary_bucket

    if not file_doc.get("client_side_encrypted"):
        raise HTTPException(status_code=400, detail="File is not client-side encrypted")

    try:
        encrypted_content = download_secure_vault_bytes(
            storage,
            object_key,
            user.username,
            bucket_override=target_bucket,
            region_override=file_doc.get("region"),
        )
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
    files_db: Collection = Depends(get_secure_files_collection),
    bucket: Optional[str] = Query(None),
):
    """
    Deletes a file from both primary and replica S3 buckets and from MongoDB.
    """
    file_doc = find_secure_file(files_db, user.username, filename, bucket)
    file_csp = file_doc.get("csp") or "AWS"
    storage = resolve_secure_storage(user.username, file_csp)
    object_key = file_doc.get("s3_key") or storage.object_key(user.username, filename)
    try:
        delete_secure_vault_object(storage, object_key)
        files_db.delete_one({"_id": file_doc["_id"]})
        return
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete file: {e}")

