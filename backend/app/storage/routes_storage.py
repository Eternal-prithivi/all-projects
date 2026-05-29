# =============================================================================
# MODULE: routes_storage.py  (274 lines)
# PURPOSE: Multi-cloud file management — ML-based placement analysis, upload
#          (AWS/GCP/Azure), list, download (access tracked), delete, AWS S3 sync
# READS FROM:  files collection, AWS/GCP/Azure cloud storage
# WRITES TO:   files collection (including access_frequency_score tracking)
# DEPENDS ON:  optimizer.py (ML ensemble), uploader.py, manager.py,
#              credential_resolver.py (BYOC support), ml/repository.py
# MOUNTED AT:  /api/storage → analyze, upload, files, download/{filename},
#              delete/{filename}, sync/aws, restore-aws/{filename}
# DO NOT:
#   - Skip access tracking on download (access_frequency_score feeds ML tiering)
#   - Change FileMetadata schema without updating tiering_tasks.py priority scoring
#   - Hardcode AWS — CSP is always read from the file record (supports GCP/Azure)
# =============================================================================
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
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
)
from app.storage.uploader import upload_to_aws, upload_to_gcp, upload_to_azure
from app.storage.optimizer import get_initial_placement_recommendation
from app.ml.repository import log_ensemble_storage_prediction
from app.utils.config import settings
from app.users.routes_users import get_current_user
from app.users.user_model import User
from app.database.mongo_client import mongodb_client
from app.storage.models_storage import FileMetadata
from app.utils.logger import setup_logger
from app.byoc.credential_resolver import resolve_aws_credentials

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
async def analyze_file_for_placement(request: AnalyzeRequest, user: User = Depends(get_current_user)):
    try:
        recommendation = get_initial_placement_recommendation(
            user_priority=request.user_priority, user_intent=request.user_intent,
            filename=request.filename, file_size_mb=request.file_size_mb,
        )
        log_ensemble_storage_prediction(
            username=user.username,
            filename=request.filename,
            file_size_mb=request.file_size_mb,
            user_priority=request.user_priority,
            user_intent=request.user_intent,
            recommendation=recommendation,
        )
        return recommendation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/upload", status_code=201)
# ... (This function remains exactly the same)
async def upload_file_to_csp(csp: str = Form(...), storage_class: str = Form(...), file: UploadFile = File(...), user: User = Depends(get_current_user), files_db: Collection = Depends(get_files_collection)):
    upload_functions = {"AWS": upload_to_aws, "GCP": upload_to_gcp, "Azure": upload_to_azure}
    upload_function = upload_functions.get(csp)
    if not upload_function:
        raise HTTPException(status_code=400, detail=f"Invalid CSP specified: {csp}")
    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        object_key = upload_function(file, user.username, file.filename, storage_class)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload to {csp} failed: {str(e)}")
    file_metadata = FileMetadata(
        filename=file.filename, s3_key=object_key, owner_username=user.username,
        size_bytes=file_size, csp=csp, storage_class=storage_class
    )
    files_db.insert_one(file_metadata.model_dump())
    return {"filename": file.filename, "csp": csp, "status": "upload successful"}

@router.get("/files")
# ... (This function remains exactly the same)
async def list_files(user: User = Depends(get_current_user), files_db: Collection = Depends(get_files_collection)):
    user_files = files_db.find({"owner_username": user.username})
    files_list = []
    for file in user_files:
        files_list.append({
            "filename": file.get("filename"), "size_bytes": file.get("size_bytes"),
            "upload_date": file.get("upload_date"), "csp": file.get("csp", "AWS"),
            "storage_class": file.get("storage_class", "Standard")
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
        bucket_name = aws["bucket_name"]
        user_prefix = f"{user.username}/"
        scanned_prefix = "" if aws.get("is_byoc") else user_prefix

        objects = list_objects_aws(
            bucket_name=bucket_name,
            prefix=scanned_prefix,
            access_key_id=aws["access_key_id"],
            secret_access_key=aws["secret_access_key"],
            session_token=aws.get("session_token"),
            region_name=aws.get("region"),
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
            ).model_dump()
            files_db.insert_one(doc)
            inserted += 1

        # --- Remove stale DB records for AWS files no longer present in S3 ---
        removed = 0
        stale_filter = {
            "owner_username": user.username,
            "csp": "AWS",
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

# --- CHANGE: The /download endpoint is now upgraded to track file access ---
@router.get("/download/{filename:path}")
async def generate_download_url(
    filename: str, 
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection)
):
    """
    Finds a file, **updates its access metadata**, determines its CSP, 
    and then calls the correct manager function to generate a download URL.
    """
    file_record = files_db.find_one({"owner_username": user.username, "filename": filename})
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in database.")

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
        url = download_function(object_key)
        return {"presigned_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate download URL from {csp}: {e}")


@router.delete("/delete/{filename:path}")
# ... (This function remains exactly the same)
async def delete_file(filename: str, user: User = Depends(get_current_user), files_db: Collection = Depends(get_files_collection)):
    file_record = files_db.find_one({"owner_username": user.username, "filename": filename})
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in database.")
    csp = file_record.get("csp")
    object_key = file_record.get("s3_key")
    delete_functions = {"AWS": delete_from_aws, "GCP": delete_from_gcp, "Azure": delete_from_azure}
    delete_function = delete_functions.get(csp)
    if not delete_function:
        raise HTTPException(status_code=500, detail=f"No delete function configured for CSP: {csp}")
    try:
        delete_function(object_key)
        files_db.delete_one({"_id": file_record["_id"]})
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": f"File '{filename}' deleted successfully from {csp}."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete file from {csp}: {e}")

@router.post("/restore-aws/{filename:path}", status_code=status.HTTP_202_ACCEPTED)
async def restore_aws_file(
    filename: str,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    tier: str = Form("Standard"), # Allowed values: 'Expedited', 'Standard', 'Bulk'
    days: int = Form(7) # How long the restored copy will be available (1-30 days)
):
    """
    Initiates a restore operation for a file stored in AWS Glacier/Deep Archive.
    """
    file_record = files_db.find_one({"owner_username": user.username, "filename": filename})
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in database.")

    if file_record.get("csp") != "AWS":
        raise HTTPException(status_code=400, detail="Restore operation is only for AWS files via this endpoint.")
    
    # Optional: You could add a check here to ensure the file is actually in Glacier
    # by calling head_object, but get_download_url_from_aws already does this when download is attempted.
    # The initiate_glacier_restore_aws function will also raise an error if it's not applicable.

    object_key = file_record.get("s3_key")

    try:
        # Call the manager function to initiate the restore
        restore_message = initiate_glacier_restore_aws(object_key, tier, days)
        return {"message": restore_message["message"]} # Return the message from the manager function
    except HTTPException as e:
        raise e # Re-raise HTTPExceptions from manager.py
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate restore for '{filename}': {e}")
