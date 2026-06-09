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
    initiate_archive_restore_gcp,
    initiate_archive_restore_azure,
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
    resolve_platform_storage_target,
)
from app.byoc.aws_bucket_discovery import (
    classify_bucket_role,
    configured_security_bucket_names,
    infer_security_bucket_by_name,
)
from app.storage.file_queries import (
    build_platform_region_list_filter,
    build_storage_list_filter,
    find_storage_file,
)
from app.cloud.availability import CloudFeature, assert_provider_available
from app.cloud.providers import normalize_provider
from app.storage.storage_errors import (
    restore_not_supported,
    validate_azure_storage_ready,
    validate_gcp_storage_ready,
)
from app.billing.storage_metering import (
    list_object_api_pages,
    record_storage_meter_event,
)
from app.storage.lifecycle_policy import (
    get_user_lifecycle_preferences,
    resolve_upload_lifecycle_policy,
    suggest_lifecycle_policy,
)
from app.storage.lifecycle_service import apply_lifecycle_action
from app.storage.lifecycle_signals import build_download_access_update
from app.storage.storage_intelligence import (
    build_cost_preview,
    build_file_insight,
    compute_portfolio_health,
    compute_savings_summary,
)

logger = setup_logger(__name__)
router = APIRouter(tags=["Storage"])


def _platform_dest_for_file_record(username: str, file_record: dict):
    """Resolve catalog destination using stored slug, account, or region (multi-region Azure)."""
    csp = file_record.get("csp")
    slug = file_record.get("platform_slug")
    if slug:
        return resolve_platform_storage_target(username, csp, region_slug=slug)
    return resolve_platform_storage_target(
        username,
        csp,
        bucket=file_record.get("cloud_bucket"),
        cloud_region=file_record.get("region"),
        account_name=file_record.get("cloud_account"),
    )


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
        account_prefs = get_user_lifecycle_preferences(user.username)
        return {
            **recommendation,
            "workflow": workflow["steps"],
            "suggested_lifecycle_policy": suggest_lifecycle_policy(
                request.user_priority,
                request.user_intent,
            ),
            "default_lifecycle_policy": account_prefs["default_lifecycle_policy"],
            "lifecycle_notice_days": account_prefs["lifecycle_notice_days"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


class LifecycleActionRequest(BaseModel):
    filename: str
    action: str
    snooze_days: int = 30


class CostPreviewRequest(BaseModel):
    file_size_mb: float
    determined_tier: str = "warm"
    user_priority: str = "balanced"
    user_intent: str = "active"
    lifecycle_policy: str = "auto"
    selected_csp: Optional[str] = None


@router.post("/lifecycle/action")
async def storage_lifecycle_action(
    body: LifecycleActionRequest,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
):
    """Respond to a pending lifecycle demotion: keep_hot, snooze, or approve."""
    try:
        return apply_lifecycle_action(
            files_db,
            user.username,
            body.filename,
            body.action,
            snooze_days=body.snooze_days,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/intelligence/cost-preview")
async def storage_cost_preview(
    body: CostPreviewRequest,
    user: User = Depends(get_current_user),
):
    """12-month what-if costs and tri-cloud comparison for upload wizard."""
    _ = user
    return build_cost_preview(
        file_size_mb=body.file_size_mb,
        determined_tier=body.determined_tier,
        user_priority=body.user_priority,
        user_intent=body.user_intent,
        lifecycle_policy=body.lifecycle_policy,
        selected_csp=body.selected_csp,
    )


@router.get("/intelligence/summary")
async def storage_intelligence_summary(
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
    platform_slug: Optional[str] = Query(None),
):
    """Portfolio health score, savings proof, and activity counts."""
    aws = resolve_aws_credentials(user.username)
    if platform_slug:
        query = build_platform_region_list_filter(user.username, platform_slug)
    else:
        query = build_storage_list_filter(user.username, bucket, None, aws["bucket_name"])
    files = list(files_db.find(query))
    reports = list(
        files_db.database["storage_lifecycle_reports"]
        .find({})
        .sort("ran_at", -1)
        .limit(31)
    )
    return {
        "health": compute_portfolio_health(files),
        "savings": compute_savings_summary(files, reports),
    }


@router.get("/intelligence/file/{filename:path}")
async def storage_file_intelligence(
    filename: str,
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
    bucket: Optional[str] = Query(None),
):
    """Detailed per-file lifecycle insight."""
    file_record = find_storage_file(files_db, user.username, filename, bucket)
    return build_file_insight(file_record)


@router.post("/upload", status_code=201)
async def upload_file_to_csp(
    csp: str = Form(...),
    storage_class: str = Form(...),
    file: UploadFile = File(...),
    bucket: Optional[str] = Form(None),
    region_slug: Optional[str] = Form(None),
    lifecycle_policy: Optional[str] = Form(None),
    user_priority: Optional[str] = Form(None),
    user_intent: Optional[str] = Form(None),
    initial_planned_tier: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    files_db: Collection = Depends(get_files_collection),
):
    try:
        csp = normalize_provider(csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    assert_provider_available(user.username, csp, CloudFeature.STORAGE)

    upload_functions = {"AWS": upload_to_aws, "GCP": upload_to_gcp, "Azure": upload_to_azure}
    upload_function = upload_functions.get(csp)
    if not upload_function:
        raise HTTPException(status_code=400, detail=f"Invalid CSP specified: {csp}")
    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        platform_dest = resolve_platform_storage_target(
            user.username,
            csp,
            region_slug=region_slug,
            bucket=bucket,
        )
        upload_bucket = bucket
        if platform_dest:
            upload_bucket = platform_dest.get("bucket") or platform_dest.get("container") or bucket

        if csp == "AWS":
            aws = resolve_aws_credentials(user.username)
            layout = get_aws_bucket_layout(user.username)
            upload_region = aws.get("region")
            if platform_dest:
                upload_region = platform_dest.get("region") or upload_region
            if upload_bucket:
                if layout and upload_bucket == layout.get("storage_bucket_name"):
                    upload_region = layout.get("primary_region") or upload_region
                elif not platform_dest:
                    from app.byoc.aws_bucket_helpers import get_bucket_actual_region

                    upload_region = (
                        get_bucket_actual_region(
                            aws["access_key_id"],
                            aws["secret_access_key"],
                            upload_bucket,
                            aws.get("session_token"),
                        )
                        or upload_region
                    )
                object_key = upload_function(
                    file,
                    user.username,
                    file.filename,
                    storage_class,
                    bucket_name=upload_bucket,
                    region_name=upload_region,
                )
            else:
                object_key = upload_function(file, user.username, file.filename, storage_class)
        elif csp == "GCP":
            object_key = upload_function(
                file,
                user.username,
                file.filename,
                storage_class,
                bucket_name=upload_bucket,
            )
        elif csp == "Azure":
            object_key = upload_function(
                file,
                user.username,
                file.filename,
                storage_class,
                container_name=upload_bucket,
                account_name=(platform_dest or {}).get("account_name"),
                account_key=(platform_dest or {}).get("account_key"),
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
    platform_dest_meta = resolve_platform_storage_target(
        user.username,
        csp,
        region_slug=region_slug,
        bucket=bucket,
    )
    cloud_bucket = (
        bucket
        or (platform_dest_meta or {}).get("bucket")
        or (platform_dest_meta or {}).get("container")
        or bucket_resolvers.get(csp, lambda _u: "")(user.username)
    )
    upload_region = None
    if csp == "AWS":
        aws = resolve_aws_credentials(user.username)
        layout = get_aws_bucket_layout(user.username)
        upload_region = aws.get("region")
        if platform_dest_meta:
            upload_region = platform_dest_meta.get("region") or upload_region
        if layout and cloud_bucket == layout.get("storage_bucket_name"):
            upload_region = layout.get("primary_region") or upload_region
        elif cloud_bucket and cloud_bucket != aws.get("bucket_name") and not platform_dest_meta:
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
    elif csp == "GCP" and cloud_bucket:
        if platform_dest_meta:
            upload_region = platform_dest_meta.get("location") or platform_dest_meta.get("region")
        else:
            try:
                from app.storage.cloud_credentials import build_gcp_storage_client

                gcs_client, _, _ = build_gcp_storage_client(user.username, bucket_name=cloud_bucket)
                gcs_bucket = gcs_client.bucket(cloud_bucket)
                if gcs_bucket.exists():
                    upload_region = gcs_bucket.location
            except Exception:
                upload_region = None
    elif csp == "Azure":
        if platform_dest_meta:
            upload_region = platform_dest_meta.get("region")
        else:
            azure = resolve_azure_credentials(user.username)
            upload_region = settings.AZURE_LOCATION or azure.get("location")

    resolved_lifecycle_policy = resolve_upload_lifecycle_policy(
        user.username,
        explicit=lifecycle_policy,
        user_priority=user_priority,
        user_intent=user_intent,
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
        platform_slug=(platform_dest_meta or {}).get("platform_slug"),
        cloud_account=(platform_dest_meta or {}).get("account_name"),
        lifecycle_policy=resolved_lifecycle_policy,
        upload_user_priority=user_priority,
        upload_user_intent=user_intent,
        initial_planned_tier=initial_planned_tier,
    )
    doc = file_metadata.model_dump()
    files_db.insert_one(doc)
    record_storage_meter_event(user.username, csp, "upload", count=1)
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
    platform_slug: Optional[str] = Query(None),
):
    aws = resolve_aws_credentials(user.username)
    default_bucket = aws["bucket_name"]
    if platform_slug:
        query = build_platform_region_list_filter(user.username, platform_slug)
    else:
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
            "platform_slug": file.get("platform_slug"),
            "cloud_account": file.get("cloud_account"),
            "s3_key": file.get("s3_key"),
            "lifecycle_policy": file.get("lifecycle_policy", "auto"),
            "lifecycle_pending_demotion": file.get("lifecycle_pending_demotion"),
            "lifecycle_snoozed_until": file.get("lifecycle_snoozed_until"),
            "initial_planned_tier": file.get("initial_planned_tier"),
            "lifecycle_savings_total_usd": file.get("lifecycle_savings_total_usd", 0),
            "insight": build_file_insight(file),
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
    region_slug: Optional[str] = Query(None),
):
    """
    On-demand storage sync for AWS S3 (free-tier friendly).

    Platform buckets are shared, so only the user's prefix is scanned. BYOC buckets
    belong to the connected user, so the whole bucket is scanned to import objects
    that may have been created outside Zenith, including Terraform-managed files.
    Stale DB records for the synced bucket/region are removed when objects are gone.
    """
    try:
        aws = resolve_aws_credentials(user.username)
        platform_dest = resolve_platform_storage_target(
            user.username,
            "AWS",
            region_slug=region_slug,
            bucket=bucket if not region_slug else None,
            cloud_region=region,
        )
        bucket_name = bucket or aws["bucket_name"]
        sync_region = region or aws.get("region")
        platform_slug = None
        if platform_dest:
            bucket_name = platform_dest.get("bucket") or bucket_name
            sync_region = platform_dest.get("region") or sync_region
            platform_slug = platform_dest.get("platform_slug")

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
            if not platform_dest and bucket_name == layout.get("storage_bucket_name"):
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

        record_storage_meter_event(
            user.username,
            "AWS",
            "list_objects",
            count=list_object_api_pages(len(objects)),
        )
        return _sync_objects_into_db(
            user=user,
            files_db=files_db,
            csp="AWS",
            objects=objects,
            bucket_name=bucket_name,
            scanned_prefix=scanned_prefix,
            is_byoc=bool(aws.get("is_byoc")),
            region=sync_region,
            platform_slug=platform_slug,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync with AWS bucket: {str(e)}")


def _stale_sync_filter(
    username: str,
    csp: str,
    bucket_name: str,
    *,
    platform_slug: str | None,
    cloud_account: str | None,
    region: str | None,
) -> dict:
    """Scope stale-record cleanup to one platform region / bucket."""
    base: dict = {"owner_username": username, "csp": csp, "cloud_bucket": bucket_name}
    if platform_slug:
        legacy = [
            {"$or": [{"platform_slug": {"$exists": False}}, {"platform_slug": None}, {"platform_slug": ""}]},
        ]
        if cloud_account:
            legacy.append({"cloud_account": cloud_account})
        elif region:
            legacy.append({"region": region})
        return {**base, "$or": [{"platform_slug": platform_slug}, {"$and": legacy}]}
    if cloud_account:
        legacy = [
            {"$or": [{"cloud_account": {"$exists": False}}, {"cloud_account": None}, {"cloud_account": ""}]},
        ]
        if region:
            legacy.append({"region": region})
        return {**base, "$or": [{"cloud_account": cloud_account}, {"$and": legacy}]}
    if region:
        return {**base, "region": region}
    return base


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
    platform_slug: str | None = None,
    cloud_account: str | None = None,
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
        existing_query: dict = {
            "owner_username": user.username,
            "cloud_bucket": bucket_name,
            "$or": [{"s3_key": object_key}, {"filename": filename}],
        }
        if platform_slug:
            legacy = [
                {
                    "$or": [
                        {"platform_slug": {"$exists": False}},
                        {"platform_slug": None},
                        {"platform_slug": ""},
                    ]
                },
            ]
            if cloud_account:
                legacy.append({"cloud_account": cloud_account})
            elif region:
                legacy.append({"region": region})
            scope = {"$or": [{"platform_slug": platform_slug}, {"$and": legacy}]}
            existing_query = {"$and": [existing_query, scope]}
        elif cloud_account:
            existing_query["cloud_account"] = cloud_account
        elif region:
            existing_query["region"] = region
        existing = files_db.find_one(existing_query)
        if existing:
            backfill: dict = {}
            if platform_slug and not existing.get("platform_slug"):
                backfill["platform_slug"] = platform_slug
            if cloud_account and not existing.get("cloud_account"):
                backfill["cloud_account"] = cloud_account
            if region and not existing.get("region"):
                backfill["region"] = region
            if backfill:
                files_db.update_one({"_id": existing["_id"]}, {"$set": backfill})
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
            platform_slug=platform_slug,
            cloud_account=cloud_account,
        ).model_dump()
        files_db.insert_one(doc)
        inserted += 1

    removed = 0
    stale_filter = _stale_sync_filter(
        user.username,
        csp,
        bucket_name,
        platform_slug=platform_slug,
        cloud_account=cloud_account,
        region=region,
    )
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
    region_slug: Optional[str] = Query(None),
):
    """On-demand GCS sync — requires platform or BYOC GCP credentials."""
    try:
        gcp = resolve_gcp_credentials(user.username)
        config_error = validate_gcp_storage_ready(gcp)
        if config_error:
            raise config_error
        platform_dest = resolve_platform_storage_target(
            user.username,
            "GCP",
            region_slug=region_slug,
            bucket=bucket if not region_slug else None,
        )
        bucket_name = bucket or gcp.get("bucket_name")
        if platform_dest:
            bucket_name = platform_dest.get("bucket") or bucket_name
        sync_region = (platform_dest or {}).get("location") or (platform_dest or {}).get("region")
        user_prefix = f"{user.username}/"
        scanned_prefix = "" if gcp.get("is_byoc") else user_prefix
        objects = list_objects_gcp(
            username=user.username,
            bucket_name=bucket_name,
            prefix=scanned_prefix,
        )
        record_storage_meter_event(
            user.username,
            "GCP",
            "list_objects",
            count=list_object_api_pages(len(objects)),
        )
        return _sync_objects_into_db(
            user=user,
            files_db=files_db,
            csp="GCP",
            objects=objects,
            bucket_name=bucket_name,
            scanned_prefix=scanned_prefix,
            is_byoc=bool(gcp.get("is_byoc")),
            region=sync_region,
            platform_slug=(platform_dest or {}).get("platform_slug"),
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
    region_slug: Optional[str] = Query(None),
):
    """On-demand Azure Blob sync — requires platform or BYOC Azure credentials."""
    try:
        azure = resolve_azure_credentials(user.username)
        config_error = validate_azure_storage_ready(azure)
        if config_error:
            raise config_error
        platform_dest = resolve_platform_storage_target(
            user.username,
            "Azure",
            region_slug=region_slug,
            bucket=container if not region_slug else None,
        )
        container_name = container or azure.get("container_name")
        if platform_dest:
            container_name = platform_dest.get("container") or platform_dest.get("bucket") or container_name
        sync_region = (platform_dest or {}).get("region")
        user_prefix = f"{user.username}/"
        scanned_prefix = "" if azure.get("is_byoc") else user_prefix
        objects = list_objects_azure(
            username=user.username,
            container_name=container_name,
            prefix=scanned_prefix,
            account_name=(platform_dest or {}).get("account_name"),
            account_key=(platform_dest or {}).get("account_key"),
        )
        record_storage_meter_event(
            user.username,
            "Azure",
            "list_objects",
            count=list_object_api_pages(len(objects)),
        )
        return _sync_objects_into_db(
            user=user,
            files_db=files_db,
            csp="Azure",
            objects=objects,
            bucket_name=container_name,
            scanned_prefix=scanned_prefix,
            is_byoc=bool(azure.get("is_byoc")),
            region=sync_region,
            platform_slug=(platform_dest or {}).get("platform_slug"),
            cloud_account=(platform_dest or {}).get("account_name"),
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
    region: Optional[str] = Query(None),
    platform_slug: Optional[str] = Query(None),
):
    """
    Finds a file, **updates its access metadata**, determines its CSP, 
    and then calls the correct manager function to generate a download URL.
    """
    file_record = find_storage_file(
        files_db,
        user.username,
        filename,
        bucket,
        region=region,
        platform_slug=platform_slug,
    )

    # --- NEW: This is the core logic for access tracking ---
    # Before we do anything else, we update the database to record this access event.
    files_db.update_one(
        {"_id": file_record["_id"]},
        build_download_access_update(),
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
        cloud_bucket = file_record.get("cloud_bucket")
        platform_dest = _platform_dest_for_file_record(user.username, file_record)
        if csp == "AWS":
            url = download_function(
                user.username,
                object_key,
                bucket_name=cloud_bucket,
                region_name=file_record.get("region"),
            )
        elif csp == "GCP":
            url = download_function(
                user.username, object_key, bucket_name=cloud_bucket
            )
        elif csp == "Azure":
            url = download_function(
                user.username,
                object_key,
                container_name=cloud_bucket,
                account_name=(platform_dest or {}).get("account_name"),
                account_key=(platform_dest or {}).get("account_key"),
            )
        else:
            url = download_function(user.username, object_key)
        record_storage_meter_event(user.username, csp, "download", count=1)
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
    region: Optional[str] = Query(None),
    platform_slug: Optional[str] = Query(None),
):
    file_record = find_storage_file(
        files_db,
        user.username,
        filename,
        bucket,
        region=region,
        platform_slug=platform_slug,
    )
    csp = file_record.get("csp")
    object_key = file_record.get("s3_key")
    delete_functions = {"AWS": delete_from_aws, "GCP": delete_from_gcp, "Azure": delete_from_azure}
    delete_function = delete_functions.get(csp)
    if not delete_function:
        raise HTTPException(status_code=500, detail=f"No delete function configured for CSP: {csp}")
    try:
        cloud_bucket = file_record.get("cloud_bucket")
        platform_dest = _platform_dest_for_file_record(user.username, file_record)
        if csp == "AWS":
            delete_function(
                user.username,
                object_key,
                bucket_name=cloud_bucket,
                region_name=file_record.get("region"),
            )
        elif csp == "GCP":
            delete_function(user.username, object_key, bucket_name=cloud_bucket)
        elif csp == "Azure":
            delete_function(
                user.username,
                object_key,
                container_name=cloud_bucket,
                account_name=(platform_dest or {}).get("account_name"),
                account_key=(platform_dest or {}).get("account_key"),
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
    """Initiate archive-tier restore for AWS Glacier, GCP ARCHIVE, or Azure Archive."""
    try:
        provider = normalize_provider(csp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    file_record = find_storage_file(files_db, user.username, filename, bucket)
    record_csp = normalize_provider(file_record.get("csp", "AWS"))
    if record_csp != provider:
        raise HTTPException(
            status_code=400,
            detail=f"File record CSP ({record_csp}) does not match restore request ({provider}).",
        )

    object_key = (
        file_record.get("s3_key")
        or file_record.get("object_key")
        or file_record.get("blob_name")
    )
    cloud_bucket = file_record.get("cloud_bucket")
    region = file_record.get("region")
    cloud_account = file_record.get("cloud_account")

    try:
        if provider == "AWS":
            restore_message = initiate_glacier_restore_aws(
                user.username,
                object_key,
                tier,
                days,
                bucket_name=cloud_bucket,
                region_name=region,
            )
            return {"message": restore_message["message"], "provider": "aws"}
        if provider == "GCP":
            restore_message = initiate_archive_restore_gcp(
                user.username,
                object_key,
                target_class="STANDARD",
                bucket_name=cloud_bucket,
            )
            return {"message": restore_message["message"], "provider": "gcp"}
        if provider == "Azure":
            restore_message = initiate_archive_restore_azure(
                user.username,
                object_key,
                target_tier="Hot",
                container_name=cloud_bucket,
                account_name=cloud_account,
                rehydrate_priority=tier if tier in ("High", "Standard") else "Standard",
            )
            return {"message": restore_message["message"], "provider": "azure"}
        raise restore_not_supported(provider)
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
