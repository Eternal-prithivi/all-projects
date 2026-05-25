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
