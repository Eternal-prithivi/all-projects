"""Tests for SHAP explainability, RL policy, and workflow orchestrator."""

from app.ml.explainability import explain_random_forest_tier
from app.ml.rl_policy import state_key_from_features, update_q_value
from app.ml.storage_ensemble import build_storage_features, predict_storage_ensemble
from app.storage.optimizer import get_file_type, get_initial_placement_recommendation


def test_storage_ensemble_includes_shap_block():
    result = predict_storage_ensemble(
        filename="backup_2026.zip",
        file_size_mb=512,
        file_type=get_file_type("backup_2026.zip"),
        user_priority="cost",
        user_intent="archival",
        rule_score=20,
        rule_tier="cold",
    )
    assert "shap_explanation" in result
    assert "available" in result["shap_explanation"]


def test_placement_recommendation_includes_shap():
    rec = get_initial_placement_recommendation(
        user_priority="cost",
        user_intent="archival",
        filename="logs_2026.tar.gz",
        file_size_mb=100,
    )
    assert "shap_explanation" in rec


def test_rl_state_key_stable():
    features = build_storage_features(
        filename="a.zip",
        file_size_mb=50,
        file_type="archive",
        user_priority="cost",
        user_intent="archival",
        rule_score=10,
        rule_tier="warm",
    )
    key_a = state_key_from_features(features)
    key_b = state_key_from_features(features)
    assert key_a == key_b


def test_rl_q_update_returns_new_value(test_database):
    features = build_storage_features(
        filename="a.zip",
        file_size_mb=5,
        file_type="document",
        user_priority="balanced",
        user_intent="frequent",
        rule_score=2,
        rule_tier="hot",
    )
    state_key = state_key_from_features(features)
    result = update_q_value(
        test_database,
        state_key=state_key,
        action_tier="hot",
        reward=0.9,
    )
    assert result["updated"] is True
    assert result["new_q"] > 0


def test_explain_random_forest_with_trained_model():
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np

    x = np.random.rand(40, 10)
    y = np.random.randint(0, 3, 40)
    model = RandomForestClassifier(n_estimators=10, random_state=0)
    model.fit(x, y)
    explanation = explain_random_forest_tier(
        model=model,
        feature_vector=list(x[0]),
        predicted_tier="warm",
    )
    assert explanation.get("available") or explanation.get("method")
