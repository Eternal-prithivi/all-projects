"""Provision intent analysis — NLP + follow-ups → template recommendation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.vm.nlp_workload import analyze_workload_nlp
from app.vm.workload_guidance import (
    assess_workload_readiness,
    build_follow_up_questions,
    merge_follow_up_answers,
)
from app.provision.template_mapper import recommend_from_text, recommendation_to_dict


def analyze_provision_intent(
    workload_description: str,
    follow_up_answers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Analyze user intent for infrastructure provisioning (not VM pool assignment).
    """
    effective = merge_follow_up_answers(workload_description or "", follow_up_answers)
    readiness = assess_workload_readiness(effective)
    follow_up_questions = build_follow_up_questions(
        readiness.get("missing_signals", []),
        follow_up_answers,
    )

    nlp_confidence = 50
    cluster_type = None
    nlp_features: Dict[str, Any] = {}
    try:
        nlp_result = analyze_workload_nlp(effective)
        nlp_confidence = nlp_result.confidence
        cluster_type = nlp_result.cluster_type
        nlp_features = dict(nlp_result.analysis_details or {})
    except Exception:
        pass

    recommendation = recommend_from_text(
        effective,
        cluster_type=cluster_type,
        nlp_confidence=nlp_confidence,
    )

    return {
        "effective_description": effective,
        "readiness": readiness,
        "follow_up_questions": follow_up_questions,
        "nlp_confidence": nlp_confidence,
        "nlp_cluster": cluster_type.value if cluster_type else None,
        "nlp_features": nlp_features,
        "recommendation": recommendation_to_dict(recommendation),
        "auto_apply_eligible": recommendation.confidence >= 70 and readiness.get("readiness_score", 0) >= 50,
    }
