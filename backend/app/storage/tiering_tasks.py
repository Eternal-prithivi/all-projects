# =============================================================================
# MODULE: tiering_tasks.py  (373 lines)
# PURPOSE: Nightly Celery Beat task — five-factor lifecycle priority scoring →
#          promotes/demotes files between hot/cool/archive storage tiers
# TASK NAME: run_nightly_tiering_lifecycle (Celery shared_task)
# SIGNALS: inactivity, access velocity, economics, cooldowns, upload intent,
#          initial ML tier, file type, CSP-aware savings (lifecycle_signals.py)
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

from app.cloud.providers import normalize_provider
from app.utils.config import settings
from app.config.demo_mode import is_demo_mode
from app.storage.manager import change_tier_on_aws, change_tier_on_gcp, change_tier_on_azure
from app.storage.optimizer import STORAGE_TIERS_DATA
from app.storage.storage_tiers import (
    COLD_TIER_NAMES,
    HOT_TIER_NAMES,
    TIER_MAP,
    WARM_TIER_NAMES,
    normalize_lifecycle_tier,
)
from app.storage.lifecycle_policy import (
    build_pending_demotion,
    demotion_thresholds,
    get_user_lifecycle_preferences,
    is_snoozed,
    pending_is_due,
    policy_allows_demotion,
)
from app.storage.lifecycle_service import (
    execute_pending_demotion,
    notify_manual_suggestion,
    notify_pending_demotion,
)
from app.storage.lifecycle_signals import (
    enhanced_priority_score,
    evaluate_demotion_eligibility,
    evaluate_promotion_eligibility,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Broadest query window (aggressive policy); per-file policy checked after fetch
_MIN_HOT_DEMOTE_DAYS = 14
_MIN_WARM_DEMOTE_DAYS = 60

# Default AWS-ish fallback when CSP unknown
TIER_MONTHLY_COST_PER_GB = {
    "hot": 0.023,
    "warm": 0.0125,
    "cold": 0.004,
}

_NOT_SENSITIVE_FILTER = {
    "$or": [
        {"is_sensitive": {"$exists": False}},
        {"is_sensitive": False},
        {"is_sensitive": None},
    ]
}


def _tier_monthly_cost_per_gb(csp: str, tier: str) -> float:
    """CSP-aware $/GB/month from optimizer pricing table."""
    options = STORAGE_TIERS_DATA.get(tier, [])
    for option in options:
        if option.get("csp") == csp:
            return float(option.get("price_per_gb", TIER_MONTHLY_COST_PER_GB.get(tier, 0.023)))
    return TIER_MONTHLY_COST_PER_GB.get(tier, 0.023)

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

    raw_csp = file_record.get("csp", "AWS")
    try:
        csp = normalize_provider(raw_csp)
    except ValueError:
        csp = "AWS"
    current_cost = _tier_monthly_cost_per_gb(csp, current_tier)
    target_cost = _tier_monthly_cost_per_gb(csp, target_tier)
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


def _inactive_days_for_demotion(file_record: Dict[str, Any], now: datetime) -> int:
    upload_age_days = _days_since(
        file_record.get("upload_date") or file_record.get("created_at"),
        now,
    )
    return _days_since(
        file_record.get("last_accessed_at") or file_record.get("last_accessed"),
        now,
        fallback_days=upload_age_days,
    )


def _meets_demotion_thresholds(
    file_record: Dict[str, Any],
    target_tier: str,
    now: datetime,
    *,
    policy: Optional[str] = None,
) -> bool:
    """Backward-compatible wrapper; full logic lives in lifecycle_signals."""
    eligible, _ = evaluate_demotion_eligibility(
        file_record, target_tier, now, policy=policy
    )
    return eligible


def _build_demotion_candidates(files_db, now: datetime) -> List[Dict[str, Any]]:
    hot_cutoff = now - timedelta(days=_MIN_HOT_DEMOTE_DAYS)
    warm_cutoff = now - timedelta(days=_MIN_WARM_DEMOTE_DAYS)

    hot_to_warm = list(files_db.find({
        "storage_class": {"$in": HOT_TIER_NAMES},
        "upload_date": {"$lt": hot_cutoff},
        "$and": [
            _NOT_SENSITIVE_FILTER,
            {"$or": [{"last_accessed_at": None}, {"last_accessed_at": {"$lt": hot_cutoff}}]},
        ],
    }))
    warm_to_cold = list(files_db.find({
        "storage_class": {"$in": WARM_TIER_NAMES},
        "last_accessed_at": {"$lt": warm_cutoff},
        **_NOT_SENSITIVE_FILTER,
    }))

    candidates: List[Dict[str, Any]] = []
    for file_record in hot_to_warm:
        eligible, signals = evaluate_demotion_eligibility(file_record, "warm", now)
        if not eligible:
            continue
        base = calculate_lifecycle_priority(file_record, "warm", now)
        priority = enhanced_priority_score(file_record, "warm", base, signals)
        candidates.append({"file_record": file_record, "target_tier": "warm", "priority": priority})
    for file_record in warm_to_cold:
        eligible, signals = evaluate_demotion_eligibility(file_record, "cold", now)
        if not eligible:
            continue
        base = calculate_lifecycle_priority(file_record, "cold", now)
        priority = enhanced_priority_score(file_record, "cold", base, signals)
        candidates.append({"file_record": file_record, "target_tier": "cold", "priority": priority})

    return sorted(candidates, key=lambda candidate: candidate["priority"]["score"], reverse=True)


def _maybe_manual_suggestion(
    files_db,
    file_record: Dict[str, Any],
    target_tier: str,
    priority: Dict[str, Any],
    now: datetime,
) -> bool:
    if file_record.get("lifecycle_policy", "auto") != "manual":
        return False
    if is_snoozed(file_record, now):
        return False
    eligible, _ = evaluate_demotion_eligibility(file_record, target_tier, now, policy="auto")
    if not eligible:
        return False
    last = file_record.get("lifecycle_last_suggestion_at")
    last_dt = _as_utc_datetime(last)
    if last_dt and (now - last_dt).days < 30:
        return False
    owner = file_record.get("owner_username")
    if not owner:
        return False
    savings = (priority.get("factors") or {}).get("estimated_monthly_savings", 0)
    notify_manual_suggestion(owner, file_record.get("filename", ""), target_tier, savings)
    files_db.update_one(
        {"_id": file_record["_id"]},
        {"$set": {"lifecycle_last_suggestion_at": now}},
    )
    return True


def _process_demotion_candidate(
    files_db,
    candidate: Dict[str, Any],
    tier_change_functions: Dict[str, Any],
    now: datetime,
) -> str:
    """
    Returns: completed | pending | skipped | failed | suggested
    """
    file_record = candidate["file_record"]
    target_tier = candidate["target_tier"]
    priority = candidate["priority"]
    policy = file_record.get("lifecycle_policy", "auto")

    if policy == "manual":
        return "suggested" if _maybe_manual_suggestion(files_db, file_record, target_tier, priority, now) else "skipped"
    if not policy_allows_demotion(policy):
        return "skipped"
    if is_snoozed(file_record, now):
        return "skipped"

    owner = file_record.get("owner_username") or ""
    notice_days = get_user_lifecycle_preferences(owner).get("lifecycle_notice_days", 7)
    pending = file_record.get("lifecycle_pending_demotion")

    if pending:
        if pending.get("target_tier") != target_tier:
            pending = build_pending_demotion(
                target_tier=target_tier,
                priority=priority,
                notice_days=notice_days,
                now=now,
            )
            files_db.update_one(
                {"_id": file_record["_id"]},
                {"$set": {"lifecycle_pending_demotion": pending}},
            )
            file_record = files_db.find_one({"_id": file_record["_id"]}) or file_record
        if pending_is_due(pending, now) or notice_days == 0:
            if execute_pending_demotion(file_record, files_db, tier_change_functions):
                return "completed"
            return "failed"
        return "pending"

    pending = build_pending_demotion(
        target_tier=target_tier,
        priority=priority,
        notice_days=notice_days,
        now=now,
    )
    files_db.update_one(
        {"_id": file_record["_id"]},
        {"$set": {"lifecycle_pending_demotion": pending}},
    )
    filename = file_record.get("filename", "")
    savings = (priority.get("factors") or {}).get("estimated_monthly_savings", 0)
    if owner:
        notify_pending_demotion(
            owner,
            filename,
            target_tier,
            savings,
            pending["execute_after"],
        )

    if notice_days == 0:
        refreshed = files_db.find_one({"_id": file_record["_id"]})
        if refreshed and execute_pending_demotion(refreshed, files_db, tier_change_functions):
            return "completed"
        return "failed"
    return "pending"


def _process_due_pending_demotions(
    files_db,
    tier_change_functions: Dict[str, Any],
    now: datetime,
) -> Dict[str, int]:
    stats = {"completed": 0, "failed": 0}
    cursor = files_db.find({"lifecycle_pending_demotion": {"$exists": True, "$ne": None}})
    for file_record in cursor:
        pending = file_record.get("lifecycle_pending_demotion")
        if not pending or not pending_is_due(pending, now):
            continue
        if is_snoozed(file_record, now):
            continue
        if not policy_allows_demotion(file_record.get("lifecycle_policy", "auto")):
            files_db.update_one(
                {"_id": file_record["_id"]},
                {"$unset": {"lifecycle_pending_demotion": ""}},
            )
            continue
        if execute_pending_demotion(file_record, files_db, tier_change_functions):
            stats["completed"] += 1
        else:
            stats["failed"] += 1
    return stats

@shared_task(name="app.storage.tiering_tasks.run_storage_optimization")
def run_storage_optimization():
    """
    The main scheduled task for the complete long-term storage optimization model.
    Handles multi-level demotions and intelligent, one-level-up promotions.
    """
    if is_demo_mode():
        logger.info("⏭️  DEMO_MODE: skipping nightly storage tiering (no cloud tier-change API calls)")
        return {"skipped": True, "reason": "demo_mode"}

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

    # --- PART 0: Execute grace-period demotions that are now due ---
    due_stats = _process_due_pending_demotions(files_db, tier_change_functions, now)

    # --- PART 1: TIERING DOWN (PRIORITIZED DEMOTION + NOTICE PERIOD) ---
    logger.info("Starting prioritized demotion analysis")
    demotion_candidates = _build_demotion_candidates(files_db, now)
    demotions_attempted = 0
    demotions_completed = due_stats["completed"]
    demotions_pending = 0
    demotions_suggested = 0
    promotions_attempted = 0
    promotions_completed = 0
    failed = due_stats["failed"]

    logger.info(f"Found {len(demotion_candidates)} prioritized demotion candidates")
    for candidate in demotion_candidates:
        demotions_attempted += 1
        outcome = _process_demotion_candidate(files_db, candidate, tier_change_functions, now)
        if outcome == "completed":
            demotions_completed += 1
        elif outcome == "pending":
            demotions_pending += 1
        elif outcome == "suggested":
            demotions_suggested += 1
        elif outcome == "failed":
            failed += 1


    # --- PART 2: TIERING UP (PROMOTION LOGIC) ---
    logger.info("Starting promotion analysis (Warm/Cold -> Hot)")
    # --- NEW RULE: Stricter time window of 5 days ---
    five_days_ago = now - timedelta(days=5)
    
    # This query implements the new, stricter "Promotion Threshold".
    promotion_pool = list(files_db.find({
        "storage_class": {"$in": WARM_TIER_NAMES + COLD_TIER_NAMES},
        "last_accessed_at": {"$gt": five_days_ago},
        **_NOT_SENSITIVE_FILTER,
    }))
    candidates_to_promote = [
        fr for fr in promotion_pool
        if evaluate_promotion_eligibility(fr, now)[0]
    ]

    logger.info(
        f"Found {len(candidates_to_promote)} promotion candidates "
        f"(from {len(promotion_pool)} recently accessed)"
    )
    for file_record in candidates_to_promote:
        normalized = normalize_lifecycle_tier(file_record.get("storage_class"))
        target_tier_name = ""
        if normalized == "cold":
            target_tier_name = "warm"
        elif normalized == "warm":
            target_tier_name = "hot"
            
        if target_tier_name:
            promotions_attempted += 1
            _, promo_signals = evaluate_promotion_eligibility(file_record, now)
            base_priority = calculate_lifecycle_priority(file_record, target_tier_name, now)
            priority = enhanced_priority_score(
                file_record,
                target_tier_name,
                base_priority,
                {"boosts": promo_signals.get("reasons", []), "metrics": promo_signals.get("metrics", {})},
            )
            changed = _perform_tier_change(
                file_record,
                target_tier_name,
                tier_change_functions,
                files_db,
                is_promotion=True,
                priority=priority,
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
        "demotions_pending": demotions_pending,
        "demotions_suggested": demotions_suggested,
        "promotion_candidates": len(candidates_to_promote),
        "promotions_attempted": promotions_attempted,
        "promotions_completed": promotions_completed,
        "failed_transitions": failed,
        "model_version": "storage_lifecycle_signals_v2",
    }
    lifecycle_reports.insert_one(summary)
    
    mongo_client.close()
    return summary

def _invoke_tier_change(
    csp: str,
    change_function,
    owner_username: str,
    object_key: str,
    new_tier_api_name: str,
    file_record: Dict[str, Any],
) -> None:
    """Pass file bucket/region/container from metadata into provider tier APIs."""
    bucket = file_record.get("cloud_bucket")
    region = file_record.get("region")
    account = file_record.get("cloud_account")
    if csp == "AWS":
        change_function(
            owner_username,
            object_key,
            new_tier_api_name,
            bucket_name=bucket,
            region_name=region,
        )
    elif csp == "GCP":
        change_function(
            owner_username,
            object_key,
            new_tier_api_name,
            bucket_name=bucket,
        )
    elif csp == "Azure":
        change_function(
            owner_username,
            object_key,
            new_tier_api_name,
            container_name=bucket,
            account_name=account,
        )
    else:
        change_function(owner_username, object_key, new_tier_api_name)


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
    raw_csp = file_record.get("csp", "AWS")
    try:
        csp = normalize_provider(raw_csp)
    except ValueError:
        logger.warning("Skipping tier change for %s: unknown CSP %r", filename, raw_csp)
        return False
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
            
            _invoke_tier_change(
                csp,
                change_function,
                owner_username,
                object_key,
                new_tier_api_name,
                file_record,
            )
            
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
                "model_version": "storage_lifecycle_signals_v2",
            },
        })
    except Exception as exc:
        logger.warning(f"Failed to write lifecycle audit entry: {exc}")
