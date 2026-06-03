"""Phase 8 feedback and retraining endpoints."""

from fastapi import APIRouter, Depends, Query

from app.database.mongo_client import get_database
from app.ml.feedback import (
    calculate_retraining_readiness,
    evaluate_feedback,
    extract_training_dataset,
    record_retraining_snapshot,
)
from app.ml.models import FeedbackEvaluationSummary, RetrainingReadiness
from app.ml.retraining import retrain_models_from_feedback
from app.ml.federated_aggregate import latest_federated_round, run_federated_statistics_round
from app.ml.rl_policy import get_policy_summary, update_policy_from_feedback
from app.ml.storage_ensemble import predict_storage_ensemble
from app.storage.optimizer import calculate_initial_placement_score, classify_storage_tier, get_file_type
from app.users.routes_users import get_current_user
from app.users.user_model import User

router = APIRouter(tags=["ML Feedback"])


@router.post("/feedback/evaluate", response_model=FeedbackEvaluationSummary)
async def evaluate_prediction_feedback(user: User = Depends(get_current_user)):
    """Evaluate due predictions/workloads in the 7-30 day feedback window."""
    summary = evaluate_feedback(get_database())
    return FeedbackEvaluationSummary(**summary)


@router.get("/feedback/readiness", response_model=RetrainingReadiness)
async def get_retraining_readiness(
    minimum_samples: int = Query(25, ge=1, le=1000),
    user: User = Depends(get_current_user),
):
    """Return whether enough high-quality feedback exists to retrain safely."""
    readiness = calculate_retraining_readiness(get_database(), minimum_samples=minimum_samples)
    return RetrainingReadiness(**readiness)


@router.get("/feedback/training-dataset")
async def get_training_dataset(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
):
    """Return filtered training samples for inspection/export."""
    return extract_training_dataset(get_database(), limit=limit)


@router.post("/feedback/retraining-snapshot")
async def create_retraining_snapshot(user: User = Depends(get_current_user)):
    """
    Store a retraining readiness snapshot.

    This is intentionally conservative: it does not deploy a model; deployment
    still requires a candidate that beats the report's absolute/relative gates.
    """
    return record_retraining_snapshot(get_database())


@router.post("/feedback/retrain")
async def retrain_from_feedback(
    minimum_samples: int = Query(25, ge=1, le=5000),
    deploy: bool = Query(True),
    user: User = Depends(get_current_user),
):
    """
    Train candidate models from evaluated user feedback and deploy only if the
    candidate beats the conservative report guardrails.
    """
    return retrain_models_from_feedback(
        get_database(),
        minimum_samples=minimum_samples,
        deploy=deploy,
    )


@router.get("/rl/policy-summary")
async def rl_policy_summary(user: User = Depends(get_current_user)):
    """Inspect learned RL Q-values (storage tier bandit)."""
    return get_policy_summary(get_database())


@router.post("/rl/update-from-feedback")
async def rl_update_from_feedback(user: User = Depends(get_current_user)):
    """Manually trigger RL policy update from evaluated feedback."""
    return update_policy_from_feedback(get_database())


@router.get("/federated/latest-round")
async def federated_latest_round(user: User = Depends(get_current_user)):
    """Latest privacy-preserving federated statistics round."""
    return latest_federated_round(get_database())


@router.post("/federated/run-round")
async def federated_run_round(user: User = Depends(get_current_user)):
    """Run a federated statistics aggregation round (admin/demo)."""
    return run_federated_statistics_round(get_database())


@router.post("/explain/storage")
async def explain_storage_prediction(
    filename: str,
    file_size_mb: float,
    user_priority: str = "balanced",
    user_intent: str = "active",
    user: User = Depends(get_current_user),
):
    """SHAP explanation for a storage tier recommendation."""
    score = calculate_initial_placement_score(user_priority, user_intent, filename, file_size_mb)
    rule_tier = classify_storage_tier(score)
    file_type = get_file_type(filename)
    ensemble = predict_storage_ensemble(
        filename=filename,
        file_size_mb=file_size_mb,
        file_type=file_type,
        user_priority=user_priority,
        user_intent=user_intent,
        rule_score=score,
        rule_tier=rule_tier,
    )
    explanation = ensemble.get("shap_explanation") or {
        "available": False,
        "reason": "SHAP explanation not generated",
    }
    return {
        "ensemble": {
            "final_tier": ensemble.get("final_tier"),
            "ensemble_confidence": ensemble.get("ensemble_confidence"),
            "expert_votes": ensemble.get("expert_votes"),
        },
        "shap_explanation": explanation,
    }
