"""
Closed-loop storage workflow orchestrator (report §3.4 Steps 1–5).

Chains preprocessing → prediction → optimization → monitoring hooks → learning
metadata in one API-friendly payload (storage upload path).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pymongo.database import Database

from app.ml.rl_policy import select_tier, state_key_from_features
from app.storage.optimizer import (
    STORAGE_TIERS_DATA,
    get_initial_placement_recommendation,
    select_best_csp_for_tier,
)


def run_storage_closed_loop_workflow(
    *,
    db: Optional[Database],
    username: str,
    filename: str,
    file_size_mb: float,
    user_priority: str,
    user_intent: str,
) -> Dict[str, Any]:
    steps: list[Dict[str, Any]] = []

    # Step 1 — workload preprocessing (filename + preferences)
    steps.append(
        {
            "step": 1,
            "name": "task_arrival_preprocessing",
            "status": "completed",
            "outputs": {
                "filename": filename,
                "file_size_mb": file_size_mb,
                "user_priority": user_priority,
                "user_intent": user_intent,
            },
        }
    )

    recommendation = get_initial_placement_recommendation(
        user_priority=user_priority,
        user_intent=user_intent,
        filename=filename,
        file_size_mb=file_size_mb,
    )

    # Step 2 — predictive modeling
    steps.append(
        {
            "step": 2,
            "name": "predictive_modeling",
            "status": "completed",
            "outputs": {
                "model_version": recommendation.get("model_version"),
                "ensemble_confidence": recommendation.get("ensemble_confidence"),
                "expert_votes": recommendation.get("expert_votes"),
            },
        }
    )

    ensemble_tier = recommendation.get("determined_tier", "hot")
    rl_meta: Dict[str, Any] = {"applied": False}
    if db is not None and recommendation.get("input_features"):
        state_key = state_key_from_features(recommendation["input_features"])
        rl_meta = select_tier(db, state_key=state_key, ensemble_tier=ensemble_tier)
        if rl_meta.get("final_tier") != ensemble_tier:
            recommendation = dict(recommendation)
            new_tier = rl_meta["final_tier"]
            recommendation["determined_tier"] = new_tier
            recommendation["recommendation"] = select_best_csp_for_tier(
                new_tier, user_priority
            )
            tier_options = STORAGE_TIERS_DATA.get(new_tier, [])
            recommendation["options_by_csp"] = {
                opt["csp"]: opt for opt in tier_options
            }
            recommendation["rl_policy"] = rl_meta
        else:
            recommendation["rl_policy"] = rl_meta
        rl_meta["applied"] = True

    # Step 3 — optimization / allocation
    steps.append(
        {
            "step": 3,
            "name": "initial_optimization_allocation",
            "status": "completed",
            "outputs": {
                "determined_tier": recommendation.get("determined_tier"),
                "recommendation": recommendation.get("recommendation"),
                "rl_policy": rl_meta,
            },
        }
    )

    # Step 4 — monitoring (deferred until upload; hooks documented)
    steps.append(
        {
            "step": 4,
            "name": "real_time_monitoring",
            "status": "scheduled",
            "outputs": {
                "note": "Access frequency and tiering_tasks Celery jobs monitor after upload.",
                "celery_tasks": [
                    "run_storage_optimization",
                    "collect_vm_metrics",
                    "check_cost_anomalies",
                ],
            },
        }
    )

    # Step 5 — learning loop metadata
    steps.append(
        {
            "step": 5,
            "name": "model_learning_update",
            "status": "pending_feedback",
            "outputs": {
                "feedback_window_days": "7-30",
                "celery_tasks": [
                    "evaluate_ml_feedback",
                    "retrain_ml_models_from_feedback",
                    "update_rl_policy_from_feedback",
                    "federated_statistics_round",
                ],
            },
        }
    )

    return {
        "workflow": "storage_closed_loop_v1",
        "username": username,
        "steps": steps,
        "recommendation": recommendation,
        "closed_loop": True,
    }
