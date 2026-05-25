"""Tests for Phase 5 ML foundation models and helpers."""

from app.ml.acceptance import (
    ENSEMBLE_TARGET_ACCURACY,
    ENSEMBLE_WEIGHT_RULE,
    NLP_AUTO_ASSIGN_CONFIDENCE,
)
from app.ml.models import ExpertName, ExpertVote, MLPredictionCreate, WorkloadClassificationCreate
from app.ml.repository import build_rule_only_storage_prediction
from app.ml.repository import build_ensemble_storage_prediction


def test_acceptance_constants_match_report():
    assert ENSEMBLE_WEIGHT_RULE == 0.30
    assert ENSEMBLE_TARGET_ACCURACY == 0.893
    assert NLP_AUTO_ASSIGN_CONFIDENCE == 0.85


def test_storage_prediction_model_validation():
    payload = MLPredictionCreate(
        username="alice",
        filename="backup.tar.gz",
        file_size_mb=512.0,
        user_priority="cost",
        user_intent="archival",
        input_features={"rule_score": 18},
        expert_votes=[
            ExpertVote(
                expert=ExpertName.RULE,
                predicted_tier="cold",
                confidence=0.62,
                weight=0.30,
            )
        ],
        final_tier="cold",
        final_csp="AWS",
        ensemble_confidence=0.62,
        rule_score=18,
    )
    assert payload.final_tier == "cold"
    assert payload.expert_votes[0].expert == ExpertName.RULE


def test_build_rule_only_storage_prediction():
    rec = {
        "analysis_score": 16,
        "determined_tier": "cold",
        "recommendation": {"csp": "GCP", "service_name": "Archive Storage"},
    }
    payload = build_rule_only_storage_prediction(
        username="bob",
        filename="archive.zip",
        file_size_mb=200.0,
        user_priority="cost",
        user_intent="archival",
        recommendation=rec,
    )
    assert payload.final_tier == "cold"
    assert payload.final_csp == "GCP"
    assert len(payload.expert_votes) == 1


def test_build_ensemble_storage_prediction():
    rec = {
        "analysis_score": 16,
        "determined_tier": "cold",
        "recommendation": {"csp": "GCP", "service_name": "Archive Storage"},
        "ensemble_confidence": 0.81,
        "tier_scores": {"hot": 0.0, "warm": 0.18, "cold": 0.81},
        "model_version": "storage_ensemble_v1",
        "model_status": {"mode": "ensemble"},
        "input_features": {"rule_score": 16},
        "expert_votes": [
            {"expert": "rule", "predicted_tier": "cold", "confidence": 0.62, "weight": 0.30},
            {"expert": "random_forest", "predicted_tier": "cold", "confidence": 0.90, "weight": 0.35},
            {"expert": "xgboost", "predicted_tier": "cold", "confidence": 0.92, "weight": 0.35},
        ],
    }
    payload = build_ensemble_storage_prediction(
        username="bob",
        filename="archive.zip",
        file_size_mb=200.0,
        user_priority="cost",
        user_intent="archival",
        recommendation=rec,
    )
    assert payload.final_tier == "cold"
    assert payload.ensemble_confidence == 0.81
    assert len(payload.expert_votes) == 3


def test_workload_classification_model():
    payload = WorkloadClassificationCreate(
        username="carol",
        workload_description="PostgreSQL database with backups",
        recommended_cluster="storage",
        final_cluster="storage",
        confidence=82,
        analysis_details={"matched_keywords": ["database"]},
    )
    assert payload.classifier_version == "keyword_v1"
    assert payload.confidence == 82
