# =============================================================================
# MODULE: routes_storage.py  (274 lines)
# PURPOSE: Multi-cloud file management — ML-based placement analysis, upload
#          (AWS/GCP/Azure), list, download (access tracked), delete, AWS S3 sync
# READS FROM:  files collection, AWS/GCP/Azure cloud storage
# WRITES TO:   files collection (including access_frequency_score tracking)
# DEPENDS ON:  optimizer.py (ML ensemble), uploader.py, manager.py,
#              credential_resolver.py (BYOC support), ml/repository.py
# MOUNTED AT:  /api/storage → analyze, upload, files, download/{filename},
#              delete/{filename}, sync/{aws|gcp|azure}, restore/{csp}/{filename}
# DO NOT:
#   - Skip access tracking on download (access_frequency_score feeds ML tiering)
#   - Change FileMetadata schema without updating tiering_tasks.py priority scoring
#   - Hardcode AWS — CSP is always read from the file record (supports GCP/Azure)
# =============================================================================
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pymongo.collection import Collection
from pydantic import BaseModel
from datetime import datetime
from botocore.config import Config
 # --- NEW: Import the datetime module ---

# Imports for all specialist functions
from app.storage.manager import (
    delete_from_aws, delete_from_gcp, delete_from_azure,
    get_download_url_from_aws, get_download_url_from_gcp, get_download_url_from_azure,
    initiate_glacier_restore_aws,
    list_objects_aws,
    list_objects_gcp,
    list_objects_azure,
)
from app.storage.uploader import upload_to_aws, upload_to_gcp, upload_to_azure
from app.storage.optimizer import get_initial_placement_recommendation
from app.ml.repository import log_ensemble_storage_prediction
from app.ml.workflow_orchestrator import run_storage_closed_loop_workflow
from app.utils.config import settings
from app.users.routes_users import get_current_user
from app.users.user_model import User
from app.database.mongo_client import mongodb_client
from app.storage.models_storage import FileMetadata
from app.utils.logger import setup_logger
from app.byoc.credential_resolver import (
    get_aws_bucket_layout,
    resolve_aws_credentials,
    resolve_azure_credentials,
    resolve_gcp_credentials,
)
from app.byoc.aws_bucket_discovery import (
    classify_bucket_role,
    configured_security_bucket_names,
    infer_security_bucket_by_name,
)
from app.storage.file_queries import (
    build_storage_list_filter,
    find_storage_file,
)
from app.cloud.providers import normalize_provider
from app.storage.storage_errors import (
    restore_not_supported,
    validate_azure_storage_ready,
    validate_gcp_storage_ready,
)

logger = setup_logger(__name__)
router = APIRouter(tags=["Storage"])

def get_files_collection() -> Collection:
    return mongodb_client.get_collection("files")

class AnalyzeRequest(BaseModel):
    filename: str
    file_size_mb: float
    user_priority: str = 'balanced'
    user_intent: str = 'active'

@router.post("/analyze")
# ... (This function remains exactly the same)
async def analyze_file_for_placement(
    request: AnalyzeRequest,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
):
    try:
        workflow = run_storage_closed_loop_workflow(
            db=files_db.database,
            username=user.username,
            filename=request.filename,
            file_size_mb=request.file_size_mb,
            user_priority=request.user_priority,
            user_intent=request.user_intent,
        )
        recommendation = workflow["recommendation"]
        log_ensemble_storage_prediction(
            username=user.username,
            filename=request.filename,
            file_size_mb=request.file_size_mb,
            user_priority=request.user_priority,
            user_intent=request.user_intent,
            recommendation=recommendation,
        )
        return {**recommendation, "workflow": workflow["steps"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/upload", status_code=201)
# ... (This function remains exactly the same)
async def upload_file_to_csp(
    csp: str = Form(...),
    storage_class: str = Form(...),
    file: UploadFile = File(...),
    bucket: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
):
    try:
        csp = normalize_provider(csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upload_functions = {"AWS": upload_to_aws, "GCP": upload_to_gcp, "Azure": upload_to_azure}
    upload_function = upload_functions.get(csp)
    if not upload_function:
        raise HTTPException(status_code=400, detail=f"Invalid CSP specified: {csp}")
    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if csp == "AWS" and bucket:
            aws = resolve_aws_credentials(user.username)
            layout = get_aws_bucket_layout(user.username)
            upload_region = aws.get("region")
            if layout and bucket == layout.get("storage_bucket_name"):
                upload_region = layout.get("primary_region") or upload_region
            elif layout:
                from app.byoc.aws_bucket_helpers import get_bucket_actual_region

                upload_region = (
                    get_bucket_actual_region(
                        aws["access_key_id"],
                        aws["secret_access_key"],
                        bucket,
                        aws.get("session_token"),
                    )
                    or upload_region
                )
            object_key = upload_function(
                file,
                user.username,
                file.filename,
                storage_class,
                bucket_name=bucket,
                region_name=upload_region,
            )
        else:
            object_key = upload_function(file, user.username, file.filename, storage_class)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload to {csp} failed: {str(e)}")
    bucket_resolvers = {
        "AWS": lambda u: resolve_aws_credentials(u)["bucket_name"],
        "GCP": lambda u: resolve_gcp_credentials(u)["bucket_name"],
        "Azure": lambda u: resolve_azure_credentials(u)["container_name"],
    }
    cloud_bucket = bucket or bucket_resolvers.get(csp, lambda _u: "")(user.username)
    upload_region = None
    if csp == "AWS":
        aws = resolve_aws_credentials(user.username)
        layout = get_aws_bucket_layout(user.username)
        upload_region = aws.get("region")
        if layout and cloud_bucket == layout.get("storage_bucket_name"):
            upload_region = layout.get("primary_region") or upload_region
        elif cloud_bucket and cloud_bucket != aws.get("bucket_name"):
            from app.byoc.aws_bucket_helpers import get_bucket_actual_region

            upload_region = (
                get_bucket_actual_region(
                    aws["access_key_id"],
                    aws["secret_access_key"],
                    cloud_bucket,
                    aws.get("session_token"),
                )
                or upload_region
            )

    file_metadata = FileMetadata(
        filename=file.filename,
        s3_key=object_key,
        owner_username=user.username,
        size_bytes=file_size,
        csp=csp,
        storage_class=storage_class,
        cloud_bucket=cloud_bucket,
        region=upload_region,
    )
    doc = file_metadata.model_dump()
    files_db.insert_one(doc)
    return {
        "filename": file.filename,
        "csp": csp,
        "status": "upload successful",
        "bucket": cloud_bucket,
        "region": upload_region,
    }

@router.get("/files")
async def list_files(
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    aws = resolve_aws_credentials(user.username)
    default_bucket = aws["bucket_name"]
    query = build_storage_list_filter(user.username, bucket, region, default_bucket)
    files_list = []
    for file in files_db.find(query):
        files_list.append({
            "filename": file.get("filename"),
            "size_bytes": file.get("size_bytes"),
            "upload_date": file.get("upload_date"),
            "csp": file.get("csp", "AWS"),
            "storage_class": file.get("storage_class", "Standard"),
            "cloud_bucket": file.get("cloud_bucket") or default_bucket,
            "region": file.get("region"),
            "s3_key": file.get("s3_key"),
        })
    return files_list


class StorageSyncResponse(BaseModel):
    inserted: int
    already_present: int
    removed: int
    skipped_non_user_prefix: int
    total_objects_seen: int
    bucket_name: str
    scanned_prefix: str


@router.post("/sync/aws", response_model=StorageSyncResponse)
async def sync_with_aws_bucket(
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """
    On-demand storage sync for AWS S3 (free-tier friendly).

    Platform buckets are shared, so only the user's prefix is scanned. BYOC buckets
    belong to the connected user, so the whole bucket is scanned to import objects
    that may have been created outside Zenith, including Terraform-managed files.
    This endpoint does not delete DB records.
    """
    try:
        aws = resolve_aws_credentials(user.username)
        bucket_name = bucket or aws["bucket_name"]
        sync_region = region or aws.get("region")
        layout = get_aws_bucket_layout(user.username)
        if layout and bucket_name:
            role = classify_bucket_role(bucket_name, layout)
            vault_names = configured_security_bucket_names(layout)
            if (
                role in ("secure", "replica")
                or bucket_name in vault_names
                or infer_security_bucket_by_name(bucket_name)
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Use the Security page to sync secure vault buckets.",
                )
            if bucket_name == layout.get("storage_bucket_name"):
                sync_region = layout.get("primary_region") or sync_region
        user_prefix = f"{user.username}/"
        scanned_prefix = "" if aws.get("is_byoc") else user_prefix

        objects = list_objects_aws(
            bucket_name=bucket_name,
            prefix=scanned_prefix,
            access_key_id=aws["access_key_id"],
            secret_access_key=aws["secret_access_key"],
            session_token=aws.get("session_token"),
            region_name=sync_region,
        )

        inserted = 0
        already_present = 0
        skipped_non_user_prefix = 0

        # Collect all valid S3 object keys so we can detect stale DB records
        live_s3_keys: set[str] = set()

        for obj in objects:
            object_key = obj.get("object_key") or ""
            if not aws.get("is_byoc") and not object_key.startswith(user_prefix):
                skipped_non_user_prefix += 1
                continue

            filename = object_key[len(user_prefix):] if object_key.startswith(user_prefix) else object_key
            if not filename:
                continue

            live_s3_keys.add(object_key)

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

            doc = FileMetadata(
                filename=filename,
                s3_key=object_key,
                owner_username=user.username,
                size_bytes=int(obj.get("size_bytes", 0) or 0),
                csp="AWS",
                storage_class=obj.get("storage_class") or "S3 Standard",
                cloud_bucket=bucket_name,
                region=sync_region,
            ).model_dump()
            files_db.insert_one(doc)
            inserted += 1

        # --- Remove stale DB records for this bucket only ---
        removed = 0
        default_bucket = aws["bucket_name"]
        if bucket_name == default_bucket:
            stale_filter: dict = {
                "owner_username": user.username,
                "csp": "AWS",
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
                "csp": "AWS",
                "cloud_bucket": bucket_name,
            }
        if live_s3_keys:
            stale_filter["s3_key"] = {"$nin": list(live_s3_keys)}
        # If live_s3_keys is empty and objects were returned (empty bucket/prefix),
        # all AWS records for this user are stale.
        # If list_objects_aws returned nothing but the call succeeded, remove all.
        stale_cursor = files_db.find(stale_filter, {"_id": 1, "filename": 1})
        stale_ids = [doc["_id"] for doc in stale_cursor]
        if stale_ids:
            result = files_db.delete_many({"_id": {"$in": stale_ids}})
            removed = result.deleted_count
            logger.info(f"Sync removed {removed} stale AWS record(s) for user {user.username}")

        return StorageSyncResponse(
            inserted=inserted,
            already_present=already_present,
            removed=removed,
            skipped_non_user_prefix=skipped_non_user_prefix,
            total_objects_seen=len(objects),
            bucket_name=bucket_name,
            scanned_prefix=scanned_prefix,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync with AWS bucket: {str(e)}")


def _sync_objects_into_db(
    *,
    user: User,
    files_db: Collection,
    csp: str,
    objects: list,
    bucket_name: str,
    scanned_prefix: str,
    is_byoc: bool,
    region: str | None,
) -> StorageSyncResponse:
    user_prefix = f"{user.username}/"
    inserted = 0
    already_present = 0
    skipped_non_user_prefix = 0
    live_keys: set[str] = set()

    for obj in objects:
        object_key = obj.get("object_key") or ""
        if not is_byoc and not object_key.startswith(user_prefix):
            skipped_non_user_prefix += 1
            continue
        filename = (
            object_key[len(user_prefix):]
            if object_key.startswith(user_prefix)
            else object_key
        )
        if not filename:
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
        doc = FileMetadata(
            filename=filename,
            s3_key=object_key,
            owner_username=user.username,
            size_bytes=int(obj.get("size_bytes", 0) or 0),
            csp=csp,
            storage_class=obj.get("storage_class") or "Standard",
            cloud_bucket=bucket_name,
            region=region,
        ).model_dump()
        files_db.insert_one(doc)
        inserted += 1

    removed = 0
    stale_filter = {
        "owner_username": user.username,
        "csp": csp,
        "cloud_bucket": bucket_name,
    }
    if live_keys:
        stale_filter["s3_key"] = {"$nin": list(live_keys)}
    stale_ids = [doc["_id"] for doc in files_db.find(stale_filter, {"_id": 1})]
    if stale_ids:
        removed = files_db.delete_many({"_id": {"$in": stale_ids}}).deleted_count

    return StorageSyncResponse(
        inserted=inserted,
        already_present=already_present,
        removed=removed,
        skipped_non_user_prefix=skipped_non_user_prefix,
        total_objects_seen=len(objects),
        bucket_name=bucket_name,
        scanned_prefix=scanned_prefix,
    )


@router.post("/sync/gcp", response_model=StorageSyncResponse)
async def sync_with_gcp_bucket(
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
):
    """On-demand GCS sync — requires platform or BYOC GCP credentials."""
    try:
        gcp = resolve_gcp_credentials(user.username)
        config_error = validate_gcp_storage_ready(gcp)
        if config_error:
            raise config_error
        bucket_name = bucket or gcp.get("bucket_name")
        user_prefix = f"{user.username}/"
        scanned_prefix = "" if gcp.get("is_byoc") else user_prefix
        objects = list_objects_gcp(
            username=user.username,
            bucket_name=bucket_name,
            prefix=scanned_prefix,
        )
        return _sync_objects_into_db(
            user=user,
            files_db=files_db,
            csp="GCP",
            objects=objects,
            bucket_name=bucket_name,
            scanned_prefix=scanned_prefix,
            is_byoc=bool(gcp.get("is_byoc")),
            region=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync with GCP bucket: {str(e)}")


@router.post("/sync/azure", response_model=StorageSyncResponse)
async def sync_with_azure_container(
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    container: Optional[str] = Query(None),
):
    """On-demand Azure Blob sync — requires platform or BYOC Azure credentials."""
    try:
        azure = resolve_azure_credentials(user.username)
        config_error = validate_azure_storage_ready(azure)
        if config_error:
            raise config_error
        container_name = container or azure.get("container_name")
        user_prefix = f"{user.username}/"
        scanned_prefix = "" if azure.get("is_byoc") else user_prefix
        objects = list_objects_azure(
            username=user.username,
            container_name=container_name,
            prefix=scanned_prefix,
        )
        return _sync_objects_into_db(
            user=user,
            files_db=files_db,
            csp="Azure",
            objects=objects,
            bucket_name=container_name,
            scanned_prefix=scanned_prefix,
            is_byoc=bool(azure.get("is_byoc")),
            region=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync with Azure container: {str(e)}")


# --- CHANGE: The /download endpoint is now upgraded to track file access ---
@router.get("/download/{filename:path}")
async def generate_download_url(
    filename: str,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
):
    """
    Finds a file, **updates its access metadata**, determines its CSP, 
    and then calls the correct manager function to generate a download URL.
    """
    file_record = find_storage_file(files_db, user.username, filename, bucket)

    # --- NEW: This is the core logic for access tracking ---
    # Before we do anything else, we update the database to record this access event.
    files_db.update_one(
        {"_id": file_record["_id"]},
        {
            "$set": {"last_accessed_at": datetime.utcnow()}, # Set the last access time to now
            "$inc": {"access_frequency_score": 1} # Increment the access counter by 1
        }
    )
    logger.debug(f"Tracked access for file '{filename}'")

    csp = file_record.get("csp")
    object_key = file_record.get("s3_key")

    download_functions = {
        "AWS": get_download_url_from_aws,
        "GCP": get_download_url_from_gcp,
        "Azure": get_download_url_from_azure
    }
    
    download_function = download_functions.get(csp)
    if not download_function:
        raise HTTPException(status_code=500, detail=f"No download function configured for CSP: {csp}")

    try:
        if csp == "AWS":
            url = download_function(
                user.username,
                object_key,
                bucket_name=file_record.get("cloud_bucket"),
                region_name=file_record.get("region"),
            )
        else:
            url = download_function(user.username, object_key)
        return {"presigned_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate download URL from {csp}: {e}")


@router.delete("/delete/{filename:path}")
# ... (This function remains exactly the same)
async def delete_file(
    filename: str,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
):
    file_record = find_storage_file(files_db, user.username, filename, bucket)
    csp = file_record.get("csp")
    object_key = file_record.get("s3_key")
    delete_functions = {"AWS": delete_from_aws, "GCP": delete_from_gcp, "Azure": delete_from_azure}
    delete_function = delete_functions.get(csp)
    if not delete_function:
        raise HTTPException(status_code=500, detail=f"No delete function configured for CSP: {csp}")
    try:
        if csp == "AWS":
            delete_function(
                user.username,
                object_key,
                bucket_name=file_record.get("cloud_bucket"),
                region_name=file_record.get("region"),
            )
        else:
            delete_function(user.username, object_key)
        files_db.delete_one({"_id": file_record["_id"]})
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": f"File '{filename}' deleted successfully from {csp}."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete file from {csp}: {e}")

@router.post("/restore/{csp}/{filename:path}", status_code=status.HTTP_202_ACCEPTED)
async def restore_archived_file(
    csp: str,
    filename: str,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    tier: str = Form("Standard"),
    days: int = Form(7),
    bucket: Optional[str] = Query(None),
):
    """Initiate archive-tier restore. AWS Glacier/Deep Archive supported; GCP/Azure return 501."""
    try:
        provider = normalize_provider(csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if provider != "AWS":
        raise restore_not_supported(provider)

    file_record = find_storage_file(files_db, user.username, filename, bucket)
    if normalize_provider(file_record.get("csp", "AWS")) != "AWS":
        raise HTTPException(
            status_code=400,
            detail="File record CSP does not match AWS restore request.",
        )

    object_key = file_record.get("s3_key")
    try:
        restore_message = initiate_glacier_restore_aws(
            user.username,
            object_key,
            tier,
            days,
            bucket_name=file_record.get("cloud_bucket"),
            region_name=file_record.get("region"),
        )
        return {"message": restore_message["message"], "provider": "aws"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate restore for '{filename}': {e}",
        )


@router.post("/restore-aws/{filename:path}", status_code=status.HTTP_202_ACCEPTED)
async def restore_aws_file_legacy(
    filename: str,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    tier: str = Form("Standard"),
    days: int = Form(7),
    bucket: Optional[str] = Query(None),
):
    """Backward-compatible alias for POST /restore/AWS/{filename}."""
    return await restore_archived_file(
        "AWS",
        filename,
        user=user,
        files_db=files_db,
        tier=tier,
        days=days,
        bucket=bucket,
    )
