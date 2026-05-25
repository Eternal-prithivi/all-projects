# =============================================================================
# MODULE: ml/storage_ensemble.py  (441 lines)
# PURPOSE: Phase 7 ML ensemble for storage tier prediction — Random Forest + XGBoost
#          vote together (weighted) to classify files into HOT/WARM/COLD/ARCHIVE
# FEATURES (10-dim): file_size_mb, access_frequency, age_days, is_sensitive,
#                    user_priority_enc, user_intent_enc, hour_of_day, day_of_week, etc.
# OUTPUT: tier prediction + confidence + expert_votes breakdown
# CALLED BY: optimizer.py → get_initial_placement_recommendation()
#            ml/retraining.py → model evaluation + guarded retrain
# DO NOT:
#   - Change feature vector order/names without retraining both models and updating feedback.py
#   - Lower the ensemble confidence threshold below 0.55 — increases mis-tier rate
#   - Import this directly from routes — always go through optimizer.py
# =============================================================================

"""
- Rule expert (30%) + Random Forest (35%) + XGBoost expert (35%)
- weighted confidence voting over hot/warm/cold tiers

If the optional xgboost package is unavailable, the XGBoost expert uses a
scikit-learn gradient-boosting fallback so storage analysis stays available.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Any, Dict, List, Tuple

import numpy as np

from app.ml.inference import STORAGE_ENSEMBLE_ARTIFACT, load_storage_ensemble_artifact
from app.ml.acceptance import (
    ENSEMBLE_WEIGHT_RANDOM_FOREST,
    ENSEMBLE_WEIGHT_RULE,
    ENSEMBLE_WEIGHT_XGBOOST,
)

TIERS: Tuple[str, ...] = ("hot", "warm", "cold")
TIER_TO_LABEL = {tier: index for index, tier in enumerate(TIERS)}
LABEL_TO_TIER = {index: tier for tier, index in TIER_TO_LABEL.items()}

FILE_TYPE_CODES = {
    "archive": 0.0,
    "data": 1.0,
    "media": 2.0,
    "document": 3.0,
}

FEATURE_NAMES: Tuple[str, ...] = (
    "file_size_mb",
    "file_type_code",
    "priority_cost",
    "priority_performance",
    "priority_balanced",
    "intent_archival",
    "intent_infrequent",
    "intent_frequent",
    "rule_score",
    "rule_tier_numeric",
)

MODEL_VERSION = "storage_ensemble_v1"


@dataclass(frozen=True)
class ExpertPrediction:
    expert: str
    predicted_tier: str
    confidence: float
    weight: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expert": self.expert,
            "predicted_tier": self.predicted_tier,
            "confidence": round(self.confidence, 4),
            "weight": self.weight,
        }


def normalize_priority(user_priority: str) -> str:
    priority = (user_priority or "balanced").strip().lower()
    return priority if priority in {"cost", "performance", "balanced"} else "balanced"


def normalize_intent(user_intent: str) -> str:
    intent = (user_intent or "active").strip().lower()
    if intent in {"active", "frequent"}:
        return "frequent"
    if intent in {"infrequent", "archival"}:
        return intent
    return "frequent"


def tier_to_numeric(tier: str) -> float:
    return float(TIER_TO_LABEL.get(tier, 0))


def build_storage_features(
    *,
    filename: str,
    file_size_mb: float,
    file_type: str,
    user_priority: str,
    user_intent: str,
    rule_score: int,
    rule_tier: str,
) -> Dict[str, float]:
    """Build the 10 report-specified features as a named dictionary."""
    priority = normalize_priority(user_priority)
    intent = normalize_intent(user_intent)
    safe_size = max(float(file_size_mb or 0.0), 0.0)
    file_type_code = FILE_TYPE_CODES.get(file_type, FILE_TYPE_CODES["document"])

    return {
        "file_size_mb": safe_size,
        "file_type_code": file_type_code,
        "priority_cost": 1.0 if priority == "cost" else 0.0,
        "priority_performance": 1.0 if priority == "performance" else 0.0,
        "priority_balanced": 1.0 if priority == "balanced" else 0.0,
        "intent_archival": 1.0 if intent == "archival" else 0.0,
        "intent_infrequent": 1.0 if intent == "infrequent" else 0.0,
        "intent_frequent": 1.0 if intent == "frequent" else 0.0,
        "rule_score": float(rule_score),
        "rule_tier_numeric": tier_to_numeric(rule_tier),
    }


def feature_vector_from_features(features: Dict[str, float]) -> List[float]:
    return [float(features[name]) for name in FEATURE_NAMES]


def _rule_tier_from_score(score: int) -> str:
    if score > 12:
        return "cold"
    if score > 5:
        return "warm"
    return "hot"


def _rule_confidence(score: int, tier: str) -> float:
    """Convert rule distance from thresholds into a calibrated confidence."""
    if tier == "cold":
        margin = score - 12
    elif tier == "warm":
        margin = min(score - 5, 12 - score)
    else:
        margin = 5 - score

    confidence = 0.55 + (max(margin, 0) / 12.0) * 0.35
    return max(0.50, min(0.92, confidence))


def _training_rule_score(
    *,
    file_size_mb: float,
    file_type: str,
    priority: str,
    intent: str,
    keyword_boost: int,
    has_date_pattern: bool,
) -> int:
    score = 0
    if priority == "cost":
        score += 5
    elif priority == "performance":
        score -= 5

    if intent == "archival":
        score += 15
    elif intent == "infrequent":
        score += 10
    elif intent == "frequent":
        score -= 5

    score += keyword_boost
    if has_date_pattern:
        score += 3

    score += {"archive": 5, "data": 3, "media": -5, "document": 0}.get(file_type, 0)
    if file_size_mb > 1024:
        score += 5
    elif file_size_mb > 100:
        score += 3
    return score


def _training_label(
    *,
    file_size_mb: float,
    file_type: str,
    priority: str,
    intent: str,
    rule_score: int,
) -> str:
    """
    Synthetic report-aligned labeler used until Phase 8 feedback data exists.

    It starts from the rule expert, then encodes the report's intended ML
    corrections: small edge-case files avoid cold storage, performance/frequent
    access pulls hotter, and large archival/cost files confidently go cold.
    """
    if priority == "performance":
        if intent == "archival" and file_type in {"archive", "data"} and file_size_mb > 1024:
            return "warm"
        return "hot"

    if intent == "frequent":
        if priority == "cost" and file_type in {"archive", "data"} and file_size_mb > 2048:
            return "warm"
        return "hot"

    if intent == "archival":
        if file_type == "media" and priority != "cost":
            return "warm"
        if file_size_mb < 25 and rule_score <= 16:
            return "warm"
        return "cold"

    if intent == "infrequent":
        if file_type == "media":
            return "hot" if file_size_mb < 250 else "warm"
        if priority == "cost" and file_size_mb > 1024 and file_type in {"archive", "data"}:
            return "cold"
        return "warm" if rule_score <= 16 else "cold"

    return _rule_tier_from_score(rule_score)


def _build_training_data() -> Tuple[np.ndarray, np.ndarray]:
    sizes = (1, 5, 10, 25, 50, 100, 250, 512, 1024, 2048, 5120, 10240)
    file_types = tuple(FILE_TYPE_CODES.keys())
    priorities = ("cost", "performance", "balanced")
    intents = ("archival", "infrequent", "frequent")
    keyword_boosts = (0, 3, 5, 8)
    date_flags = (False, True)

    rows: List[List[float]] = []
    labels: List[int] = []
    for file_size_mb, file_type, priority, intent, keyword_boost, has_date in product(
        sizes,
        file_types,
        priorities,
        intents,
        keyword_boosts,
        date_flags,
    ):
        rule_score = _training_rule_score(
            file_size_mb=file_size_mb,
            file_type=file_type,
            priority=priority,
            intent=intent,
            keyword_boost=keyword_boost,
            has_date_pattern=has_date,
        )
        rule_tier = _rule_tier_from_score(rule_score)
        features = build_storage_features(
            filename="synthetic",
            file_size_mb=file_size_mb,
            file_type=file_type,
            user_priority=priority,
            user_intent=intent,
            rule_score=rule_score,
            rule_tier=rule_tier,
        )
        label = _training_label(
            file_size_mb=file_size_mb,
            file_type=file_type,
            priority=priority,
            intent=intent,
            rule_score=rule_score,
        )
        rows.append(feature_vector_from_features(features))
        labels.append(TIER_TO_LABEL[label])

    return np.array(rows, dtype=float), np.array(labels, dtype=int)


@lru_cache(maxsize=1)
def _load_expert_models() -> Dict[str, Any]:
    try:
        artifact = load_storage_ensemble_artifact()
        if artifact and artifact.get("random_forest") is not None and artifact.get("xgboost") is not None:
            return {
                "available": True,
                "random_forest": artifact["random_forest"],
                "xgboost": artifact["xgboost"],
                "xgboost_backend": artifact.get("xgboost_backend", "artifact"),
                "error": None,
                "artifact_path": str(STORAGE_ENSEMBLE_ARTIFACT),
                "training_samples": artifact.get("training_samples"),
                "test_accuracy": artifact.get("test_accuracy"),
                "artifact_model_version": artifact.get("model_version"),
            }

        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

        x_train, y_train = _build_training_data()

        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            max_features=3,
            random_state=42,
        )
        rf_model.fit(x_train, y_train)

        try:
            from xgboost import XGBClassifier  # type: ignore

            xgb_model = XGBClassifier(
                n_estimators=100,
                max_depth=10,
                learning_rate=0.1,
                objective="multi:softprob",
                eval_metric="mlogloss",
                random_state=42,
                n_jobs=1,
            )
            xgb_backend = "xgboost"
        except Exception:
            xgb_model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3,
                random_state=42,
            )
            xgb_backend = "sklearn_gradient_boosting_fallback"

        xgb_model.fit(x_train, y_train)
        return {
            "available": True,
            "random_forest": rf_model,
            "xgboost": xgb_model,
            "xgboost_backend": xgb_backend,
            "error": None,
            "artifact_path": None,
            "training_samples": len(y_train),
            "test_accuracy": None,
            "artifact_model_version": None,
        }
    except Exception as exc:
        return {
            "available": False,
            "random_forest": None,
            "xgboost": None,
            "xgboost_backend": "unavailable",
            "error": str(exc),
            "artifact_path": None,
            "training_samples": None,
            "test_accuracy": None,
            "artifact_model_version": None,
        }


def _model_vote(model: Any, features: List[float], expert: str, weight: float) -> ExpertPrediction:
    probabilities = model.predict_proba([features])[0]
    classes = list(model.classes_)
    best_index = int(np.argmax(probabilities))
    label = int(classes[best_index])
    return ExpertPrediction(
        expert=expert,
        predicted_tier=LABEL_TO_TIER.get(label, "hot"),
        confidence=float(probabilities[best_index]),
        weight=weight,
    )


def _weighted_vote(votes: List[ExpertPrediction]) -> Tuple[str, float, Dict[str, float]]:
    tier_scores = {tier: 0.0 for tier in TIERS}
    for vote in votes:
        tier_scores[vote.predicted_tier] += vote.confidence * vote.weight

    final_tier = max(TIERS, key=lambda tier: (tier_scores[tier], -TIER_TO_LABEL[tier]))
    confidence = tier_scores[final_tier]
    return final_tier, confidence, {tier: round(score, 4) for tier, score in tier_scores.items()}


def predict_storage_ensemble(
    *,
    filename: str,
    file_size_mb: float,
    file_type: str,
    user_priority: str,
    user_intent: str,
    rule_score: int,
    rule_tier: str,
) -> Dict[str, Any]:
    features_by_name = build_storage_features(
        filename=filename,
        file_size_mb=file_size_mb,
        file_type=file_type,
        user_priority=user_priority,
        user_intent=user_intent,
        rule_score=rule_score,
        rule_tier=rule_tier,
    )
    feature_vector = feature_vector_from_features(features_by_name)

    votes = [
        ExpertPrediction(
            expert="rule",
            predicted_tier=rule_tier,
            confidence=_rule_confidence(rule_score, rule_tier),
            weight=ENSEMBLE_WEIGHT_RULE,
        )
    ]

    model_status = _load_expert_models()
    if model_status["available"]:
        votes.append(
            _model_vote(
                model_status["random_forest"],
                feature_vector,
                "random_forest",
                ENSEMBLE_WEIGHT_RANDOM_FOREST,
            )
        )
        votes.append(
            _model_vote(
                model_status["xgboost"],
                feature_vector,
                "xgboost",
                ENSEMBLE_WEIGHT_XGBOOST,
            )
        )

    final_tier, confidence, tier_scores = _weighted_vote(votes)
    return {
        "model_version": MODEL_VERSION,
        "final_tier": final_tier,
        "ensemble_confidence": round(confidence, 4),
        "tier_scores": tier_scores,
        "expert_votes": [vote.to_dict() for vote in votes],
        "input_features": features_by_name,
        "feature_vector": feature_vector,
        "model_status": {
            "mode": "ensemble" if model_status["available"] else "rule_fallback",
            "xgboost_backend": model_status["xgboost_backend"],
            "error": model_status["error"],
            "artifact_path": model_status.get("artifact_path"),
            "training_samples": model_status.get("training_samples"),
            "test_accuracy": model_status.get("test_accuracy"),
            "artifact_model_version": model_status.get("artifact_model_version"),
        },
    }


def clear_storage_ensemble_cache() -> None:
    _load_expert_models.cache_clear()
