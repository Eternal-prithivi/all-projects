"""SHAP-based explainability for storage ensemble predictions (report §3 layer 7)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.ml.storage_ensemble import FEATURE_NAMES, LABEL_TO_TIER, TIER_TO_LABEL, TIERS


def _fallback_feature_attribution(
    model: Any,
    feature_vector: List[float],
    predicted_tier: str,
) -> Dict[str, Any]:
    """Use tree feature importances when SHAP is unavailable."""
    importances = getattr(model, "feature_importances_", None)
    if importances is None or len(importances) != len(feature_vector):
        return {
            "method": "feature_importance_fallback",
            "available": False,
            "reason": "Model does not expose feature_importances_",
            "top_features": [],
        }

    weighted = [
        {
            "feature": FEATURE_NAMES[i],
            "impact": round(float(importances[i] * feature_vector[i]), 6),
            "value": round(float(feature_vector[i]), 4),
        }
        for i in range(len(FEATURE_NAMES))
    ]
    weighted.sort(key=lambda row: abs(row["impact"]), reverse=True)
    return {
        "method": "feature_importance_fallback",
        "available": True,
        "predicted_tier": predicted_tier,
        "top_features": weighted[:6],
        "summary": _human_summary(weighted[:3], predicted_tier),
    }


def _human_summary(top_rows: List[Dict[str, Any]], predicted_tier: str) -> str:
    if not top_rows:
        return f"The ensemble recommended {predicted_tier} tier storage."
    drivers = ", ".join(row["feature"].replace("_", " ") for row in top_rows[:3])
    return (
        f"Recommended {predicted_tier} tier mainly because of: {drivers}."
    )


def explain_random_forest_tier(
    *,
    model: Any,
    feature_vector: List[float],
    predicted_tier: str,
    background_samples: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Explain the Random Forest expert vote using SHAP TreeExplainer when possible.
    """
    if model is None:
        return {"method": "none", "available": False, "reason": "Model not loaded"}

    try:
        import shap  # type: ignore

        x = np.array([feature_vector], dtype=float)
        explainer = shap.TreeExplainer(model, data=background_samples)
        shap_values = explainer.shap_values(x)

        label_idx = TIER_TO_LABEL.get(predicted_tier, 0)
        if isinstance(shap_values, list):
            if label_idx >= len(shap_values):
                label_idx = 0
            row_values = np.asarray(shap_values[label_idx][0], dtype=float)
            base_value = float(explainer.expected_value[label_idx])
        else:
            row_values = np.asarray(shap_values[0], dtype=float)
            base_value = float(getattr(explainer, "expected_value", 0.0))

        contributions = [
            {
                "feature": FEATURE_NAMES[i],
                "shap_value": round(float(row_values[i]), 6),
                "feature_value": round(float(feature_vector[i]), 4),
            }
            for i in range(len(FEATURE_NAMES))
        ]
        contributions.sort(key=lambda row: abs(row["shap_value"]), reverse=True)
        top = contributions[:6]

        return {
            "method": "shap_tree",
            "available": True,
            "predicted_tier": predicted_tier,
            "base_value": round(base_value, 6),
            "top_features": top,
            "summary": _human_summary(
                [{"feature": row["feature"], "impact": row["shap_value"]} for row in top],
                predicted_tier,
            ),
        }
    except Exception as exc:
        fallback = _fallback_feature_attribution(model, feature_vector, predicted_tier)
        fallback["shap_error"] = str(exc)[:200]
        return fallback


def build_storage_explanation(
    *,
    ensemble_result: Dict[str, Any],
    rf_model: Any,
) -> Dict[str, Any]:
    """Attach SHAP explanation for the ensemble's Random Forest expert."""
    predicted_tier = ensemble_result.get("final_tier", "hot")
    feature_vector = ensemble_result.get("feature_vector") or []
    if not feature_vector:
        return {"available": False, "reason": "Missing feature vector"}

    explanation = explain_random_forest_tier(
        model=rf_model,
        feature_vector=feature_vector,
        predicted_tier=predicted_tier,
    )
    explanation["ensemble_tier_scores"] = ensemble_result.get("tier_scores", {})
    explanation["expert_votes"] = ensemble_result.get("expert_votes", [])
    return explanation
