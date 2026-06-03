"""Celery tasks for Phase 8 ML feedback evaluation."""

from celery import shared_task
from pymongo import MongoClient

from app.ml.feedback import evaluate_feedback, record_retraining_snapshot
from app.ml.federated_aggregate import run_federated_statistics_round
from app.ml.retraining import retrain_models_from_feedback
from app.ml.rl_policy import update_policy_from_feedback
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@shared_task(name="evaluate_ml_feedback")
def evaluate_ml_feedback():
    """Daily low-cost feedback evaluation for storage/workload predictions."""
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    try:
        db = mongo_client["CloudResourceOptimizationDB"]
        summary = evaluate_feedback(db)
        snapshot = record_retraining_snapshot(db)
        rl_summary = update_policy_from_feedback(db)
        logger.info(
            "ML feedback evaluation complete: "
            f"{summary}; retraining_ready={snapshot.get('ready_for_retraining')}; "
            f"rl_states_updated={rl_summary.get('states_updated')}"
        )
        return {"summary": summary, "readiness": snapshot, "rl_policy": rl_summary}
    finally:
        mongo_client.close()


@shared_task(name="retrain_ml_models_from_feedback")
def retrain_ml_models_from_feedback(minimum_samples: int = 25):
    """Weekly guarded retraining from evaluated storage/workload feedback."""
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    try:
        db = mongo_client["CloudResourceOptimizationDB"]
        summary = evaluate_feedback(db)
        retraining = retrain_models_from_feedback(
            db,
            minimum_samples=minimum_samples,
            deploy=True,
        )
        logger.info(
            "ML feedback retraining complete: "
            f"status={retraining.get('status')}; deployed={retraining.get('deployed')}"
        )
        return {"summary": summary, "retraining": retraining}
    finally:
        mongo_client.close()


@shared_task(name="update_rl_policy_from_feedback")
def update_rl_policy_from_feedback_task():
    """Daily RL policy update from evaluated storage feedback."""
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    try:
        db = mongo_client["CloudResourceOptimizationDB"]
        return update_policy_from_feedback(db)
    finally:
        mongo_client.close()


@shared_task(name="federated_statistics_round")
def federated_statistics_round_task():
    """Weekly federated statistics aggregation (privacy-preserving buckets)."""
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    try:
        db = mongo_client["CloudResourceOptimizationDB"]
        return run_federated_statistics_round(db)
    finally:
        mongo_client.close()
