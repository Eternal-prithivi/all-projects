"""Persistence helpers for ML prediction and workload classification logs."""

from typing import Any, Dict, List, Optional

from app.database.mongo_client import get_database
from app.ml.acceptance import (
    ENSEMBLE_WEIGHT_RULE,
    ENSEMBLE_WEIGHT_RANDOM_FOREST,
    ENSEMBLE_WEIGHT_XGBOOST,
)
from app.ml.models import (
    EvaluationStatus,
    ExpertName,
    ExpertVote,
    MLPredictionCreate,
    MLPredictionRecord,
    WorkloadClassificationCreate,
    WorkloadClassificationRecord,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

ML_PREDICTIONS = "ml_predictions"
ML_WORKLOAD_DESCRIPTIONS = "ml_workload_descriptions"


def _predictions_collection():
    return get_database()[ML_PREDICTIONS]


def _workload_collection():
    return get_database()[ML_WORKLOAD_DESCRIPTIONS]


def log_storage_prediction(payload: MLPredictionCreate) -> Optional[str]:
    """Insert a storage-tier prediction record. Returns inserted id as string."""
    try:
        doc = MLPredictionRecord(**payload.model_dump()).model_dump()
        result = _predictions_collection().insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.warning(f"Failed to log storage prediction: {e}")
        return None


def log_workload_classification(payload: WorkloadClassificationCreate) -> Optional[str]:
    """Insert a workload classification record. Returns inserted id as string."""
    try:
        doc = WorkloadClassificationRecord(**payload.model_dump()).model_dump()
        result = _workload_collection().insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.warning(f"Failed to log workload classification: {e}")
        return None


def build_rule_only_storage_prediction(
    *,
    username: str,
    filename: str,
    file_size_mb: float,
    user_priority: str,
    user_intent: str,
    recommendation: Dict[str, Any],
) -> MLPredictionCreate:
    """
    Phase 5: log rule expert only until RF/XGBoost are implemented (Phase 7).
    """
    tier = recommendation.get("determined_tier", "hot")
    rule_score = recommendation.get("analysis_score", 0)
    best = recommendation.get("recommendation") or {}

    # Map rule score to a simple 0–1 confidence for the single expert
    if rule_score > 12:
        rule_confidence = 0.62
    elif rule_score > 5:
        rule_confidence = 0.75
    else:
        rule_confidence = 0.88

    return MLPredictionCreate(
        username=username,
        filename=filename,
        file_size_mb=file_size_mb,
        user_priority=user_priority,
        user_intent=user_intent,
        input_features={
            "filename": filename,
            "file_size_mb": file_size_mb,
            "user_priority": user_priority,
            "user_intent": user_intent,
            "rule_score": rule_score,
        },
        expert_votes=[
            ExpertVote(
                expert=ExpertName.RULE,
                predicted_tier=tier,
                confidence=rule_confidence,
                weight=ENSEMBLE_WEIGHT_RULE,
            ),
        ],
        final_tier=tier,
        final_csp=best.get("csp"),
        final_service=best.get("service_name"),
        ensemble_confidence=rule_confidence,
        rule_score=rule_score,
    )


def build_ensemble_storage_prediction(
    *,
    username: str,
    filename: str,
    file_size_mb: float,
    user_priority: str,
    user_intent: str,
    recommendation: Dict[str, Any],
) -> MLPredictionCreate:
    """
    Phase 7: build a log payload from the RF + XGBoost weighted ensemble.

    Falls back to the Phase 5 rule-only payload if older recommendation shapes
    reach this helper.
    """
    raw_votes = recommendation.get("expert_votes") or []
    if not raw_votes:
        return build_rule_only_storage_prediction(
            username=username,
            filename=filename,
            file_size_mb=file_size_mb,
            user_priority=user_priority,
            user_intent=user_intent,
            recommendation=recommendation,
        )

    votes: List[ExpertVote] = []
    for vote in raw_votes:
        try:
            expert_name = ExpertName(vote.get("expert", "rule"))
        except ValueError:
            expert_name = ExpertName.RULE
        votes.append(
            ExpertVote(
                expert=expert_name,
                predicted_tier=vote.get("predicted_tier"),
                confidence=float(vote.get("confidence", 0.0)),
                weight=float(vote.get("weight", 0.0)),
            )
        )

    tier = recommendation.get("determined_tier", "hot")
    rule_score = recommendation.get("analysis_score", 0)
    best = recommendation.get("recommendation") or {}
    input_features = recommendation.get("input_features") or {
        "filename": filename,
        "file_size_mb": file_size_mb,
        "user_priority": user_priority,
        "user_intent": user_intent,
        "rule_score": rule_score,
    }

    return MLPredictionCreate(
        username=username,
        filename=filename,
        file_size_mb=file_size_mb,
        user_priority=user_priority,
        user_intent=user_intent,
        input_features={
            **input_features,
            "tier_scores": recommendation.get("tier_scores", {}),
            "model_version": recommendation.get("model_version"),
            "model_status": recommendation.get("model_status", {}),
        },
        expert_votes=votes,
        final_tier=tier,
        final_csp=best.get("csp"),
        final_service=best.get("service_name"),
        ensemble_confidence=float(recommendation.get("ensemble_confidence", 0.0)),
        rule_score=rule_score,
    )


def log_ensemble_storage_prediction(
    *,
    username: str,
    filename: str,
    file_size_mb: float,
    user_priority: str,
    user_intent: str,
    recommendation: Dict[str, Any],
) -> Optional[str]:
    """Convenience: build and persist a Phase 7 ensemble prediction log."""
    payload = build_ensemble_storage_prediction(
        username=username,
        filename=filename,
        file_size_mb=file_size_mb,
        user_priority=user_priority,
        user_intent=user_intent,
        recommendation=recommendation,
    )
    return log_storage_prediction(payload)


def log_rule_only_storage_prediction(
    *,
    username: str,
    filename: str,
    file_size_mb: float,
    user_priority: str,
    user_intent: str,
    recommendation: Dict[str, Any],
) -> Optional[str]:
    """Convenience: build and persist a rule-only prediction log entry."""
    payload = build_rule_only_storage_prediction(
        username=username,
        filename=filename,
        file_size_mb=file_size_mb,
        user_priority=user_priority,
        user_intent=user_intent,
        recommendation=recommendation,
    )
    return log_storage_prediction(payload)


def build_workload_log_from_analysis(
    *,
    username: str,
    workload_description: str,
    recommended_cluster: str,
    final_cluster: str,
    confidence: int,
    analysis_details: Dict[str, Any],
    user_overrode: bool,
) -> WorkloadClassificationCreate:
    classifier_version = analysis_details.get("classifier_version", "keyword_v1")
    raw_nlp = analysis_details.get("nlp_features", {})
    nlp_features = raw_nlp if isinstance(raw_nlp, dict) else {}

    return WorkloadClassificationCreate(
        username=username,
        workload_description=workload_description,
        recommended_cluster=recommended_cluster,
        final_cluster=final_cluster,
        confidence=confidence,
        classifier_version=classifier_version,
        nlp_features=nlp_features if isinstance(nlp_features, dict) else {},
        analysis_details=analysis_details,
        user_overrode_recommendation=user_overrode,
    )
