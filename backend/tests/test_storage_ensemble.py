"""Tests for Phase 7 storage-tier ensemble."""

import pytest

from app.ml.acceptance import (
    ENSEMBLE_WEIGHT_RANDOM_FOREST,
    ENSEMBLE_WEIGHT_RULE,
    ENSEMBLE_WEIGHT_XGBOOST,
)
from app.ml.storage_ensemble import (
    FEATURE_NAMES,
    TIERS,
    build_storage_features,
    feature_vector_from_features,
    predict_storage_ensemble,
)
from app.storage.optimizer import get_file_type, get_initial_placement_recommendation


def test_storage_feature_vector_matches_report_contract():
    features = build_storage_features(
        filename="backup_2026-05-24.zip",
        file_size_mb=2048,
        file_type="archive",
        user_priority="cost",
        user_intent="archival",
        rule_score=28,
        rule_tier="cold",
    )
    vector = feature_vector_from_features(features)

    assert len(FEATURE_NAMES) == 10
    assert len(vector) == 10
    assert features["priority_cost"] == 1.0
    assert features["intent_archival"] == 1.0
    assert features["rule_tier_numeric"] == 2.0


def test_ensemble_returns_three_weighted_expert_votes():
    result = predict_storage_ensemble(
        filename="backup_2026-05-24.zip",
        file_size_mb=2048,
        file_type=get_file_type("backup_2026-05-24.zip"),
        user_priority="cost",
        user_intent="archival",
        rule_score=28,
        rule_tier="cold",
    )

    votes = result["expert_votes"]
    assert result["final_tier"] in TIERS
    assert result["model_status"]["mode"] == "ensemble"
    assert {vote["expert"] for vote in votes} == {"rule", "random_forest", "xgboost"}
    assert sum(vote["weight"] for vote in votes) == pytest.approx(
        ENSEMBLE_WEIGHT_RULE + ENSEMBLE_WEIGHT_RANDOM_FOREST + ENSEMBLE_WEIGHT_XGBOOST
    )
    assert result["ensemble_confidence"] > 0


def test_storage_optimizer_preserves_response_shape_with_ensemble_metadata():
    recommendation = get_initial_placement_recommendation(
        user_priority="cost",
        user_intent="archival",
        filename="backup_2026-05-24.zip",
        file_size_mb=2048,
    )

    assert recommendation["determined_tier"] == "cold"
    assert recommendation["recommendation"]["csp"] in {"AWS", "GCP", "Azure"}
    assert recommendation["options_by_csp"]
    assert len(recommendation["expert_votes"]) == 3
    assert recommendation["model_version"] == "storage_ensemble_v1"
