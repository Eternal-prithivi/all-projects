"""Feedback-driven model retraining and guarded deployment."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import accuracy_score

from app.ml.acceptance import RETRAIN_MIN_ABSOLUTE_GAIN, RETRAIN_MIN_RELATIVE_GAIN
from app.ml.feedback import (
    RETRAINING_COLLECTION,
    STORAGE_COLLECTION,
    WORKLOAD_COLLECTION,
    _eligible_filter,
    calculate_retraining_readiness,
)
from app.ml.inference import (
    ARTIFACT_DIR,
    STORAGE_ENSEMBLE_ARTIFACT,
    WORKLOAD_CLASSIFIER_ARTIFACT,
    clear_model_artifact_cache,
)
from app.ml.sample_datasets import generate_storage_training_rows, generate_workload_training_rows
from app.ml.storage_ensemble import FEATURE_NAMES, TIER_TO_LABEL, clear_storage_ensemble_cache
from app.ml.training import train_storage_ensemble, train_workload_classifier

REPORT_CLUSTERS = {"general", "storage", "memory", "performance", "ai_ml"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _storage_feedback_rows(db, limit: int) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    cursor = db[STORAGE_COLLECTION].find(_eligible_filter()).sort("evaluated_at", -1).limit(limit)
    for sample in cursor:
        features = sample.get("input_features") or {}
        details = sample.get("evaluation_details") or {}
        label_tier = details.get("actual_tier") or sample.get("final_tier")
        if label_tier not in TIER_TO_LABEL:
            continue

        try:
            row = {name: float(features[name]) for name in FEATURE_NAMES}
        except (KeyError, TypeError, ValueError):
            continue

        row["label_tier"] = str(label_tier)
        row["feedback_score"] = float(sample.get("feedback_score", 0.0) or 0.0)
        rows.append(row)
    return rows


def _workload_feedback_rows(db, limit: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    cursor = db[WORKLOAD_COLLECTION].find(_eligible_filter()).sort("evaluated_at", -1).limit(limit)
    for sample in cursor:
        description = (sample.get("workload_description") or "").strip()
        label_cluster = sample.get("final_cluster") or (sample.get("evaluation_details") or {}).get("final_cluster")
        if not description or label_cluster not in REPORT_CLUSTERS:
            continue

        rows.append({"workload_description": description, "label_cluster": str(label_cluster)})
    return rows


def _evaluate_storage_candidate(artifact: Dict[str, Any], feedback_rows: List[Dict[str, object]]) -> Optional[float]:
    if not feedback_rows:
        return None

    x_data = np.array([[float(row[name]) for name in FEATURE_NAMES] for row in feedback_rows], dtype=float)
    y_data = np.array([TIER_TO_LABEL[str(row["label_tier"])] for row in feedback_rows], dtype=int)
    rf_accuracy = accuracy_score(y_data, artifact["random_forest"].predict(x_data))
    xgb_accuracy = accuracy_score(y_data, artifact["xgboost"].predict(x_data))
    return round(float((rf_accuracy + xgb_accuracy) / 2), 4)


def _evaluate_workload_candidate(artifact: Dict[str, Any], feedback_rows: List[Dict[str, str]]) -> Optional[float]:
    if not feedback_rows:
        return None

    pipeline = artifact["pipeline"]
    descriptions = [row["workload_description"] for row in feedback_rows]
    labels = [row["label_cluster"] for row in feedback_rows]
    return round(float(accuracy_score(labels, pipeline.predict(descriptions))), 4)


def _weighted_candidate_score(
    *,
    storage_score: Optional[float],
    storage_count: int,
    workload_score: Optional[float],
    workload_count: int,
) -> float:
    weighted_total = 0.0
    total = 0
    if storage_score is not None:
        weighted_total += storage_score * storage_count
        total += storage_count
    if workload_score is not None:
        weighted_total += workload_score * workload_count
        total += workload_count
    return round(weighted_total / total, 4) if total else 0.0


def _meets_deployment_guard(candidate_score: float, current_score: float) -> Dict[str, Any]:
    absolute_gain = candidate_score - current_score
    relative_gain = absolute_gain / max(current_score, 0.01)
    passed = absolute_gain >= RETRAIN_MIN_ABSOLUTE_GAIN or relative_gain >= RETRAIN_MIN_RELATIVE_GAIN
    return {
        "passed": passed,
        "absolute_gain": round(float(absolute_gain), 4),
        "relative_gain": round(float(relative_gain), 4),
        "minimum_absolute_gain": RETRAIN_MIN_ABSOLUTE_GAIN,
        "minimum_relative_gain": RETRAIN_MIN_RELATIVE_GAIN,
    }


def _deploy_candidate(candidate_path: Path, active_path: Path) -> None:
    active_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate_path, active_path)


def retrain_models_from_feedback(
    db,
    *,
    minimum_samples: int = 25,
    deploy: bool = True,
    include_synthetic_seed: bool = True,
    feedback_limit: int = 2000,
) -> Dict[str, Any]:
    """
    Train candidate storage/workload artifacts from eligible feedback.

    Deployment is guarded: the candidate must beat the current feedback baseline
    by the report's absolute or relative threshold before replacing active
    artifacts.
    """
    now = datetime.now(timezone.utc)
    readiness = calculate_retraining_readiness(db, minimum_samples=minimum_samples)
    if not readiness["ready_for_retraining"]:
        result = {
            **readiness,
            "trained_at": now,
            "model_type": "feedback_retraining",
            "status": "skipped",
            "deployed": False,
            "deployment_reason": readiness["deployment_guard"]["reason"],
            "candidate": None,
        }
        inserted = db[RETRAINING_COLLECTION].insert_one(result)
        result["_id"] = str(inserted.inserted_id)
        return result

    storage_feedback = _storage_feedback_rows(db, feedback_limit)
    workload_feedback = _workload_feedback_rows(db, feedback_limit)

    storage_rows: List[Dict[str, object]] = []
    workload_rows: List[Dict[str, str]] = []
    if include_synthetic_seed:
        storage_rows.extend(generate_storage_training_rows(repeats=4))
        workload_rows.extend(generate_workload_training_rows(repeats=20))
    storage_rows.extend(storage_feedback)
    workload_rows.extend(workload_feedback)

    candidate_dir = ARTIFACT_DIR / "candidates" / _timestamp()
    storage_candidate_path = candidate_dir / "storage_ensemble.joblib"
    workload_candidate_path = candidate_dir / "workload_classifier.joblib"

    storage_artifact = train_storage_ensemble(
        storage_rows,
        artifact_path=storage_candidate_path,
        model_version="storage_ensemble_v1.feedback_retrained",
    )
    workload_artifact = train_workload_classifier(
        workload_rows,
        artifact_path=workload_candidate_path,
        model_version="workload_text_ensemble_v2.feedback_retrained",
    )

    storage_score = _evaluate_storage_candidate(storage_artifact, storage_feedback)
    workload_score = _evaluate_workload_candidate(workload_artifact, workload_feedback)
    candidate_score = _weighted_candidate_score(
        storage_score=storage_score,
        storage_count=len(storage_feedback),
        workload_score=workload_score,
        workload_count=len(workload_feedback),
    )
    current_score = float(readiness.get("current_feedback_accuracy", 0.0) or 0.0)
    guard = _meets_deployment_guard(candidate_score, current_score)
    should_deploy = bool(deploy and guard["passed"])

    if should_deploy:
        _deploy_candidate(storage_candidate_path, STORAGE_ENSEMBLE_ARTIFACT)
        _deploy_candidate(workload_candidate_path, WORKLOAD_CLASSIFIER_ARTIFACT)
        clear_model_artifact_cache()
        clear_storage_ensemble_cache()

    result = {
        **readiness,
        "trained_at": now,
        "model_type": "feedback_retraining",
        "status": "deployed" if should_deploy else "candidate_trained",
        "deployed": should_deploy,
        "deployment_reason": "guard_passed" if should_deploy else "candidate_did_not_beat_guard",
        "candidate": {
            "storage_artifact": str(storage_candidate_path),
            "workload_artifact": str(workload_candidate_path),
            "storage_feedback_samples": len(storage_feedback),
            "workload_feedback_samples": len(workload_feedback),
            "storage_training_samples": len(storage_rows),
            "workload_training_samples": len(workload_rows),
            "storage_feedback_accuracy": storage_score,
            "workload_feedback_accuracy": workload_score,
            "candidate_feedback_accuracy": candidate_score,
            "current_feedback_accuracy": current_score,
            "deployment_guard": guard,
            "storage_test_accuracy": storage_artifact.get("test_accuracy"),
            "workload_test_accuracy": workload_artifact.get("test_accuracy"),
            "xgboost_backend": storage_artifact.get("xgboost_backend"),
            "workload_model": "tfidf_soft_voting_logreg_nb_random_forest",
        },
    }
    inserted = db[RETRAINING_COLLECTION].insert_one(result)
    result["_id"] = str(inserted.inserted_id)
    return result
