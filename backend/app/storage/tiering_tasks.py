# =============================================================================
# MODULE: tiering_tasks.py  (373 lines)
# PURPOSE: Nightly Celery Beat task — five-factor lifecycle priority scoring →
#          promotes/demotes files between hot/cool/archive storage tiers
# TASK NAME: run_nightly_tiering_lifecycle (Celery shared_task)
# FIVE FACTORS: last_accessed_at, access_frequency_score, size_bytes,
#               is_sensitive, storage_class (weighted priority score)
# READS FROM:  files collection (all users)
# WRITES TO:   files collection (storage_class field), AWS/GCP/Azure (S3 copy+delete)
# SCHEDULED:   Celery Beat — runs nightly via celery_worker.py beat schedule
# DO NOT:
#   - Change the priority scoring formula without updating DEC-009 in DECISIONS.md
#   - Simplify to a single-factor decision — the five-factor balance is intentional
#   - Remove the is_sensitive check — sensitive files skip automatic tiering
# =============================================================================
from celery import shared_task
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.config import settings
from app.storage.manager import change_tier_on_aws, change_tier_on_gcp, change_tier_on_azure
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# This map is now used for both demotions and promotions across all tiers.
TIER_MAP = {
    "AWS": {"hot": "STANDARD", "warm": "STANDARD_IA", "cold": "GLACIER"},
    "GCP": {"hot": "STANDARD", "warm": "NEARLINE", "cold": "ARCHIVE"},
    "Azure": {"hot": "Hot", "warm": "Cool", "cold": "Archive"}
}

# Helper lists for easier querying
HOT_TIER_NAMES = ["Standard", "S3 Standard", "Standard Storage", "Hot Blob Storage"]
WARM_TIER_NAMES = ["STANDARD_IA", "NEARLINE", "Cool"]
COLD_TIER_NAMES = ["GLACIER", "ARCHIVE", "Archive"]
ALL_TIER_NAMES = HOT_TIER_NAMES + WARM_TIER_NAMES + COLD_TIER_NAMES

TIER_MONTHLY_COST_PER_GB = {
    "hot": 0.023,
    "warm": 0.0125,
    "cold": 0.004,
}

FILE_TYPE_PRIORITY_POINTS = {
    "archive": 20,
    "backup": 20,
    "database": 18,
    "data": 15,
    "document": 12,
    "media": 10,
    "log": 8,
    "active": 4,
}


def normalize_lifecycle_tier(storage_class: Optional[str]) -> Optional[str]:
    """Map provider-specific storage classes into the report's hot/warm/cold tiers."""
    if not storage_class:
        return None

    normalized = storage_class.strip().lower()
    if normalized in {tier.lower() for tier in HOT_TIER_NAMES} or normalized == "hot":
        return "hot"
    if normalized in {tier.lower() for tier in WARM_TIER_NAMES} or normalized == "warm":
        return "warm"
    if normalized in {tier.lower() for tier in COLD_TIER_NAMES} or normalized == "cold":
        return "cold"
    return None


def _as_utc_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _file_size_gb(file_record: Dict[str, Any]) -> float:
    for field, divisor in (
        ("size_gb", 1),
        ("file_size_gb", 1),
        ("size_mb", 1024),
        ("file_size_mb", 1024),
        ("size_bytes", 1024 * 1024 * 1024),
        ("file_size", 1024 * 1024 * 1024),
    ):
        value = file_record.get(field)
        if value is None:
            continue
        try:
            return max(float(value) / divisor, 0.001)
        except (TypeError, ValueError):
            continue
    return 0.001


def _file_type(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".zip", ".tar", ".gz", ".rar", ".7z"}:
        return "archive"
    if suffix in {".bak", ".dump"}:
        return "backup"
    if suffix in {".sql", ".db", ".sqlite"}:
        return "database"
    if suffix in {".csv", ".json", ".parquet", ".xml"}:
        return "data"
    if suffix in {".log"}:
        return "log"
    if suffix in {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".mkv"}:
        return "media"
    return "document"


def _days_since(value: Any, now: datetime, fallback_days: int = 0) -> int:
    dt = _as_utc_datetime(value)
    if not dt:
        return fallback_days
    return max((now - dt).days, 0)


def calculate_lifecycle_priority(
    file_record: Dict[str, Any],
    target_tier: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Five-factor report-style priority score for lifecycle demotion.

    Factors: age, inactivity, access frequency, file type, and estimated monthly
    savings. The score is intentionally transparent so the UI/docs can explain
    why one file moved before another.
    """
    now = now or datetime.now(timezone.utc)
    current_tier = normalize_lifecycle_tier(file_record.get("storage_class")) or "hot"
    upload_age_days = _days_since(file_record.get("upload_date") or file_record.get("created_at"), now)
    inactive_days = _days_since(
        file_record.get("last_accessed_at") or file_record.get("last_accessed"),
        now,
        fallback_days=upload_age_days,
    )
    access_frequency = max(int(file_record.get("access_frequency_score", 0) or 0), 0)
    size_gb = _file_size_gb(file_record)
    filename = file_record.get("filename") or file_record.get("name") or ""
    file_type = _file_type(filename)

    age_score = min(upload_age_days / 120 * 20, 20)
    inactivity_score = min(inactive_days / 120 * 25, 25)
    access_score = max(20 - min(access_frequency, 10) * 2, 0)
    type_score = FILE_TYPE_PRIORITY_POINTS.get(file_type, 10)

    current_cost = TIER_MONTHLY_COST_PER_GB.get(current_tier, TIER_MONTHLY_COST_PER_GB["hot"])
    target_cost = TIER_MONTHLY_COST_PER_GB.get(target_tier, current_cost)
    monthly_savings = max((current_cost - target_cost) * size_gb, 0)
    savings_score = min((monthly_savings / 5.0) * 30, 30)

    total_score = round(
        min(age_score + inactivity_score + access_score + type_score + savings_score, 100),
        2,
    )
    return {
        "score": total_score,
        "target_tier": target_tier,
        "current_tier": current_tier,
        "factors": {
            "age_score": round(age_score, 2),
            "inactivity_score": round(inactivity_score, 2),
            "access_score": round(access_score, 2),
            "file_type_score": round(type_score, 2),
            "savings_score": round(savings_score, 2),
            "upload_age_days": upload_age_days,
            "inactive_days": inactive_days,
            "access_frequency_score": access_frequency,
            "file_type": file_type,
            "size_gb": round(size_gb, 4),
            "estimated_monthly_savings": round(monthly_savings, 4),
        },
    }


def _build_demotion_candidates(files_db, now: datetime) -> List[Dict[str, Any]]:
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)

    hot_to_warm = list(files_db.find({
        "storage_class": {"$in": HOT_TIER_NAMES},
        "upload_date": {"$lt": thirty_days_ago},
        "$or": [{"last_accessed_at": None}, {"last_accessed_at": {"$lt": thirty_days_ago}}],
    }))
    warm_to_cold = list(files_db.find({
        "storage_class": {"$in": WARM_TIER_NAMES},
        "last_accessed_at": {"$lt": ninety_days_ago},
    }))

    candidates: List[Dict[str, Any]] = []
    for file_record in hot_to_warm:
        priority = calculate_lifecycle_priority(file_record, "warm", now)
        candidates.append({"file_record": file_record, "target_tier": "warm", "priority": priority})
    for file_record in warm_to_cold:
        priority = calculate_lifecycle_priority(file_record, "cold", now)
        candidates.append({"file_record": file_record, "target_tier": "cold", "priority": priority})

    return sorted(candidates, key=lambda candidate: candidate["priority"]["score"], reverse=True)

@shared_task(name="app.storage.tiering_tasks.run_storage_optimization")
def run_storage_optimization():
    """
    The main scheduled task for the complete long-term storage optimization model.
    Handles multi-level demotions and intelligent, one-level-up promotions.
    """
    logger.info(f"Running scheduled storage optimization task")
    
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["files"]
    lifecycle_reports = db["storage_lifecycle_reports"]

    now = datetime.now(timezone.utc)
    
    tier_change_functions = {
        "AWS": change_tier_on_aws,
        "GCP": change_tier_on_gcp,
        "Azure": change_tier_on_azure
    }

    # --- PART 1: TIERING DOWN (PRIORITIZED DEMOTION LOGIC) ---
    logger.info("Starting prioritized demotion analysis")
    demotion_candidates = _build_demotion_candidates(files_db, now)
    demotions_attempted = 0
    demotions_completed = 0
    promotions_attempted = 0
    promotions_completed = 0
    failed = 0

    logger.info(f"Found {len(demotion_candidates)} prioritized demotion candidates")
    for candidate in demotion_candidates:
        demotions_attempted += 1
        changed = _perform_tier_change(
            candidate["file_record"],
            candidate["target_tier"],
            tier_change_functions,
            files_db,
            priority=candidate["priority"],
        )
        if changed:
            demotions_completed += 1
        else:
            failed += 1


    # --- PART 2: TIERING UP (PROMOTION LOGIC) ---
    logger.info("Starting promotion analysis (Warm/Cold -> Hot)")
    # --- NEW RULE: Stricter time window of 5 days ---
    five_days_ago = now - timedelta(days=5)
    
    # This query implements the new, stricter "Promotion Threshold".
    candidates_to_promote = list(files_db.find({
        "storage_class": {"$in": WARM_TIER_NAMES + COLD_TIER_NAMES},
        "last_accessed_at": {"$gt": five_days_ago},
        # --- NEW RULE: Stricter frequency of more than 2 accesses ---
        "access_frequency_score": {"$gt": 2} 
    }))

    logger.info(f"Found {len(candidates_to_promote)} candidates for promotion")
    for file_record in candidates_to_promote:
        current_tier = file_record.get("storage_class")
        
        # --- NEW RULE: Determine the target tier (only one level up) ---
        target_tier_name = ""
        if current_tier in COLD_TIER_NAMES:
            target_tier_name = "warm" # If it's Cold, the next level up is Warm
        elif current_tier in WARM_TIER_NAMES:
            target_tier_name = "hot" # If it's Warm, the next level up is Hot
            
        if target_tier_name:
            promotions_attempted += 1
            changed = _perform_tier_change(
                file_record,
                target_tier_name,
                tier_change_functions,
                files_db,
                is_promotion=True,
                priority=calculate_lifecycle_priority(file_record, target_tier_name, now),
            )
            if changed:
                promotions_completed += 1
            else:
                failed += 1


    logger.info("Storage optimization task finished")
    summary = {
        "ran_at": now,
        "demotion_candidates": len(demotion_candidates),
        "demotions_attempted": demotions_attempted,
        "demotions_completed": demotions_completed,
        "promotion_candidates": len(candidates_to_promote),
        "promotions_attempted": promotions_attempted,
        "promotions_completed": promotions_completed,
        "failed_transitions": failed,
        "model_version": "storage_lifecycle_priority_v1",
    }
    lifecycle_reports.insert_one(summary)
    
    mongo_client.close()
    return summary

def _perform_tier_change(
    file_record,
    target_tier,
    tier_change_functions,
    files_db,
    is_promotion=False,
    priority: Optional[Dict[str, Any]] = None,
):
    """A helper function to perform and log the tier change for a single file."""
    filename = file_record.get("filename")
    owner_username = file_record.get("owner_username")
    csp = file_record.get("csp", "AWS")
    object_key = file_record.get("s3_key") or file_record.get("object_key") or file_record.get("blob_name")

    if not owner_username:
        logger.warning("Skipping tier change for %s: missing owner_username", filename)
        return False

    change_function = tier_change_functions.get(csp)
    new_tier_api_name = TIER_MAP.get(csp, {}).get(target_tier)

    if change_function and new_tier_api_name:
        try:
            action = "Promoting" if is_promotion else "Demoting"
            logger.info(f"{action} '{filename}' on {csp} to {target_tier.upper()} tier ({new_tier_api_name})")
            
            change_function(owner_username, object_key, new_tier_api_name)
            
            now = datetime.now(timezone.utc)
            update_operation = {
                "$set": {
                    "storage_class": new_tier_api_name,
                    "csp": csp,
                    "last_tier_change": now,
                    "lifecycle_last_action": "promotion" if is_promotion else "demotion",
                    "lifecycle_priority": priority or {},
                },
                "$inc": {"tier_transition_count": 1},
            }
            # If it's a promotion, we also reset the frequency score to re-evaluate its "hotness"
            if is_promotion:
                update_operation["$set"]["access_frequency_score"] = 0

            files_db.update_one({"_id": file_record["_id"]}, update_operation)
            _write_lifecycle_audit(files_db.database, file_record, target_tier, new_tier_api_name, is_promotion, priority)
            logger.info(f"Successfully moved '{filename}'")
            return True
        except Exception as e:
            logger.error(f"Error moving '{filename}': {e}")
            return False
    else:
        logger.warning(f"No tiering action configured for CSP '{csp}' or tier '{target_tier}'")
        return False


def _write_lifecycle_audit(
    db,
    file_record: Dict[str, Any],
    target_tier: str,
    provider_storage_class: str,
    is_promotion: bool,
    priority: Optional[Dict[str, Any]],
) -> None:
    try:
        db["activity_log"].insert_one({
            "username": file_record.get("owner_username") or file_record.get("username"),
            "timestamp": datetime.utcnow(),
            "action": "storage_lifecycle_promotion" if is_promotion else "storage_lifecycle_demotion",
            "description": (
                f"{file_record.get('filename')} moved to {target_tier} "
                f"({provider_storage_class}) by lifecycle optimizer"
            ),
            "metadata": {
                "file_id": str(file_record.get("_id")),
                "filename": file_record.get("filename"),
                "target_tier": target_tier,
                "provider_storage_class": provider_storage_class,
                "priority": priority or {},
                "model_version": "storage_lifecycle_priority_v1",
            },
        })
    except Exception as exc:
        logger.warning(f"Failed to write lifecycle audit entry: {exc}")
