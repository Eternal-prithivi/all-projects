"""Phase 8 feedback evaluation and guarded retraining readiness.

This module implements the report §4.5 loop without paid infrastructure:
stored predictions are evaluated after the 7-30 day outcome window, noisy
samples are filtered by feedback score, and retraining readiness is reported
with conservative deployment guardrails.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bson import ObjectId
from pymongo.database import Database

from app.ml.acceptance import (
    FEEDBACK_EVALUATION_WINDOW_DAYS_MAX,
    FEEDBACK_EVALUATION_WINDOW_DAYS_MIN,
    FEEDBACK_MIN_SCORE_FOR_TRAINING,
    RETRAIN_MIN_ABSOLUTE_GAIN,
    RETRAIN_MIN_RELATIVE_GAIN,
)
from app.ml.models import EvaluationStatus, OutcomeQuality

STORAGE_COLLECTION = "ml_predictions"
WORKLOAD_COLLECTION = "ml_workload_descriptions"
RETRAINING_COLLECTION = "ml_retraining_runs"

HOT_TIER_NAMES = {
    "hot",
    "standard",
    "s3 standard",
    "standard storage",
    "hot blob storage",
    "hot",
}
WARM_TIER_NAMES = {
    "warm",
    "standard_ia",
    "s3 standard-ia",
    "nearline",
    "nearline storage",
    "cool",
    "cool blob storage",
}
COLD_TIER_NAMES = {
    "cold",
    "glacier",
    "s3 glacier flexible",
    "deep_archive",
    "archive",
    "archive storage",
}


def _now() -> datetime:
    return datetime.utcnow()


def _age_days(created_at: Any, now: datetime) -> Optional[int]:
    if not isinstance(created_at, datetime):
        return None
    return max((now - created_at).days, 0)


def normalize_storage_tier(storage_class: Optional[str]) -> Optional[str]:
    if not storage_class:
        return None
    normalized = storage_class.strip().lower()
    if normalized in HOT_TIER_NAMES:
        return "hot"
    if normalized in WARM_TIER_NAMES:
        return "warm"
    if normalized in COLD_TIER_NAMES:
        return "cold"
    return None


def _tier_distance(left: str, right: str) -> int:
    order = {"hot": 0, "warm": 1, "cold": 2}
    return abs(order.get(left, 0) - order.get(right, 0))


def classify_feedback_score(score: float) -> OutcomeQuality:
    if score >= 0.80:
        return OutcomeQuality.GOOD
    if score >= FEEDBACK_MIN_SCORE_FOR_TRAINING:
        return OutcomeQuality.ACCEPTABLE
    return OutcomeQuality.BAD


def _storage_feedback_from_file(prediction: Dict[str, Any], file_record: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    predicted_tier = prediction.get("final_tier") or "hot"
    actual_tier = normalize_storage_tier(file_record.get("storage_class"))
    if not actual_tier:
        return 0.0, {"reason": "unknown_storage_class", "storage_class": file_record.get("storage_class")}

    distance = _tier_distance(predicted_tier, actual_tier)
    if distance == 0:
        score = 0.95
    elif distance == 1:
        score = 0.65
    else:
        score = 0.25

    access_score = int(file_record.get("access_frequency_score", 0) or 0)
    if predicted_tier == "cold" and access_score > 2:
        score = min(score, 0.45)
    elif predicted_tier == "hot" and access_score == 0 and actual_tier in {"warm", "cold"}:
        score = min(score, 0.60)

    upload_dt = prediction.get("created_at") or file_record.get("upload_date") or file_record.get("created_at")
    days_since_upload = _age_days(upload_dt, _now()) if upload_dt else None
    recommended_csp = prediction.get("final_csp")
    actual_csp = file_record.get("csp")
    csp_override = False
    if recommended_csp and actual_csp:
        try:
            from app.cloud.providers import normalize_provider
            csp_override = normalize_provider(recommended_csp) != normalize_provider(actual_csp)
        except ValueError:
            csp_override = str(recommended_csp) != str(actual_csp)

    return score, {
        "predicted_tier": predicted_tier,
        "actual_tier": actual_tier,
        "storage_class": file_record.get("storage_class"),
        "access_frequency_score": access_score,
        "tier_distance": distance,
        "days_since_upload": days_since_upload,
        "recommended_csp": recommended_csp,
        "actual_csp": actual_csp,
        "csp_override": csp_override,
    }


def _workload_feedback(workload: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    confidence = max(min(float(workload.get("confidence", 0) or 0) / 100.0, 1.0), 0.0)
    recommended = workload.get("recommended_cluster")
    final = workload.get("final_cluster")
    user_overrode = bool(workload.get("user_overrode_recommendation", False))

    if user_overrode and final != recommended:
        score = 0.35 if confidence >= 0.75 else 0.55
    elif final == recommended:
        score = max(0.75, confidence)
    else:
        score = 0.50

    return score, {
        "recommended_cluster": recommended,
        "final_cluster": final,
        "confidence": confidence,
        "user_overrode_recommendation": user_overrode,
    }


def _eligible_window_query(now: datetime) -> Dict[str, Any]:
    min_created = now - timedelta(days=FEEDBACK_EVALUATION_WINDOW_DAYS_MAX)
    max_created = now - timedelta(days=FEEDBACK_EVALUATION_WINDOW_DAYS_MIN)
    return {
        "evaluation_status": EvaluationStatus.PENDING.value,
        "created_at": {"$gte": min_created, "$lte": max_created},
    }


def _too_old_query(now: datetime) -> Dict[str, Any]:
    return {
        "evaluation_status": EvaluationStatus.PENDING.value,
        "created_at": {"$lt": now - timedelta(days=FEEDBACK_EVALUATION_WINDOW_DAYS_MAX)},
    }


def _mark_skipped(collection, doc_id: ObjectId, reason: str, now: datetime) -> None:
    collection.update_one(
        {"_id": doc_id},
        {
            "$set": {
                "evaluation_status": EvaluationStatus.SKIPPED.value,
                "outcome_quality": None,
                "feedback_score": None,
                "evaluated_at": now,
                "evaluation_details": {"reason": reason},
            }
        },
    )


def evaluate_storage_predictions(db: Database, now: Optional[datetime] = None) -> Dict[str, int]:
    now = now or _now()
    predictions = db[STORAGE_COLLECTION]
    files = db["files"]
    stats = {"evaluated": 0, "skipped": 0, "pending": 0}

    for prediction in predictions.find(_eligible_window_query(now)):
        filename = prediction.get("filename")
        username = prediction.get("username")
        file_record = files.find_one({"owner_username": username, "filename": filename})
        if not file_record:
            _mark_skipped(predictions, prediction["_id"], "file_record_missing", now)
            stats["skipped"] += 1
            continue

        score, details = _storage_feedback_from_file(prediction, file_record)
        quality = classify_feedback_score(score)
        predictions.update_one(
            {"_id": prediction["_id"]},
            {
                "$set": {
                    "evaluation_status": EvaluationStatus.EVALUATED.value,
                    "outcome_quality": quality.value,
                    "feedback_score": score,
                    "evaluated_at": now,
                    "evaluation_details": details,
                }
            },
        )
        stats["evaluated"] += 1

    for prediction in predictions.find(_too_old_query(now)):
        _mark_skipped(predictions, prediction["_id"], "evaluation_window_expired", now)
        stats["skipped"] += 1

    stats["pending"] = predictions.count_documents({"evaluation_status": EvaluationStatus.PENDING.value})
    return stats


def evaluate_workload_predictions(db: Database, now: Optional[datetime] = None) -> Dict[str, int]:
    now = now or _now()
    workloads = db[WORKLOAD_COLLECTION]
    stats = {"evaluated": 0, "skipped": 0, "pending": 0}

    for workload in workloads.find(_eligible_window_query(now)):
        score, details = _workload_feedback(workload)
        quality = classify_feedback_score(score)
        workloads.update_one(
            {"_id": workload["_id"]},
            {
                "$set": {
                    "evaluation_status": EvaluationStatus.EVALUATED.value,
                    "outcome_quality": quality.value,
                    "feedback_score": score,
                    "evaluated_at": now,
                    "evaluation_details": details,
                }
            },
        )
        stats["evaluated"] += 1

    for workload in workloads.find(_too_old_query(now)):
        _mark_skipped(workloads, workload["_id"], "evaluation_window_expired", now)
        stats["skipped"] += 1

    stats["pending"] = workloads.count_documents({"evaluation_status": EvaluationStatus.PENDING.value})
    return stats


def evaluate_feedback(db: Database, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    storage = evaluate_storage_predictions(db, now)
    workload = evaluate_workload_predictions(db, now)
    eligible = count_training_eligible_samples(db)
    return {
        "evaluated_predictions": storage["evaluated"],
        "skipped_predictions": storage["skipped"],
        "pending_predictions": storage["pending"],
        "evaluated_workloads": workload["evaluated"],
        "skipped_workloads": workload["skipped"],
        "pending_workloads": workload["pending"],
        "training_eligible_samples": eligible["total"],
    }


def _eligible_filter() -> Dict[str, Any]:
    return {
        "evaluation_status": EvaluationStatus.EVALUATED.value,
        "feedback_score": {"$gte": FEEDBACK_MIN_SCORE_FOR_TRAINING},
    }


def count_training_eligible_samples(db: Database) -> Dict[str, int]:
    storage_count = db[STORAGE_COLLECTION].count_documents(_eligible_filter())
    workload_count = db[WORKLOAD_COLLECTION].count_documents(_eligible_filter())
    return {
        "storage": storage_count,
        "workload": workload_count,
        "total": storage_count + workload_count,
    }


def extract_training_dataset(db: Database, limit: int = 500) -> Dict[str, Any]:
    storage_samples = list(db[STORAGE_COLLECTION].find(_eligible_filter()).sort("evaluated_at", -1).limit(limit))
    workload_samples = list(db[WORKLOAD_COLLECTION].find(_eligible_filter()).sort("evaluated_at", -1).limit(limit))
    return {
        "storage_samples": [_serialize_training_sample(sample, "storage_tier") for sample in storage_samples],
        "workload_samples": [_serialize_training_sample(sample, "workload_cluster") for sample in workload_samples],
    }


def _serialize_training_sample(sample: Dict[str, Any], sample_type: str) -> Dict[str, Any]:
    payload = {
        "id": str(sample.get("_id")),
        "type": sample_type,
        "feedback_score": sample.get("feedback_score"),
        "outcome_quality": sample.get("outcome_quality"),
        "created_at": sample.get("created_at"),
        "evaluated_at": sample.get("evaluated_at"),
    }
    if sample_type == "storage_tier":
        payload.update(
            {
                "input_features": sample.get("input_features", {}),
                "final_tier": sample.get("final_tier"),
                "evaluation_details": sample.get("evaluation_details", {}),
            }
        )
    else:
        payload.update(
            {
                "workload_description": sample.get("workload_description"),
                "final_cluster": sample.get("final_cluster"),
                "nlp_features": sample.get("nlp_features", {}),
                "analysis_details": sample.get("analysis_details", {}),
            }
        )
    return payload


def calculate_retraining_readiness(db: Database, minimum_samples: int = 25) -> Dict[str, Any]:
    counts = count_training_eligible_samples(db)
    total = counts["total"]
    storage_scores = _feedback_scores(db[STORAGE_COLLECTION].find(_eligible_filter()))
    workload_scores = _feedback_scores(db[WORKLOAD_COLLECTION].find(_eligible_filter()))
    all_scores = storage_scores + workload_scores
    current_accuracy = sum(all_scores) / len(all_scores) if all_scores else 0.0
    ready = total >= minimum_samples

    deployment_guard = {
        "minimum_absolute_gain": RETRAIN_MIN_ABSOLUTE_GAIN,
        "minimum_relative_gain": RETRAIN_MIN_RELATIVE_GAIN,
        "candidate_model_required": True,
        "status": "ready_to_train" if ready else "needs_more_feedback",
        "reason": None if ready else f"Need at least {minimum_samples} eligible samples.",
    }

    return {
        "ready_for_retraining": ready,
        "eligible_samples": total,
        "storage_samples": counts["storage"],
        "workload_samples": counts["workload"],
        "current_feedback_accuracy": round(current_accuracy, 4),
        "minimum_feedback_score": FEEDBACK_MIN_SCORE_FOR_TRAINING,
        "deployment_guard": deployment_guard,
    }


def _feedback_scores(samples: Iterable[Dict[str, Any]]) -> List[float]:
    scores: List[float] = []
    for sample in samples:
        try:
            scores.append(float(sample.get("feedback_score", 0.0)))
        except (TypeError, ValueError):
            continue
    return scores


def record_retraining_snapshot(db: Database, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    readiness = calculate_retraining_readiness(db)
    last_deploy = db[RETRAINING_COLLECTION].find_one(
        {"deployed": True},
        sort=[("trained_at", -1)],
    )
    last_deploy_summary = None
    if last_deploy:
        last_deploy_summary = {
            "trained_at": last_deploy.get("trained_at"),
            "candidate_accuracy": last_deploy.get("candidate_accuracy"),
            "baseline_accuracy": last_deploy.get("baseline_accuracy"),
            "deployment_reason": last_deploy.get("deployment_reason"),
        }
    snapshot = {
        **readiness,
        "trained_at": now,
        "deployed": False,
        "deployment_reason": readiness["deployment_guard"]["status"],
        "model_type": "feedback_snapshot",
        "last_successful_deploy": last_deploy_summary,
    }
    result = db[RETRAINING_COLLECTION].insert_one(snapshot)
    snapshot["_id"] = str(result.inserted_id)
    if isinstance(snapshot.get("trained_at"), datetime):
        snapshot["trained_at"] = snapshot["trained_at"].isoformat()
    return snapshot
