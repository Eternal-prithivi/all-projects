"""Provision intent analysis — NLP + follow-ups → template recommendation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.vm.nlp_workload import analyze_workload_nlp
from app.vm.contextual_followups import build_contextual_follow_up_questions
from app.vm.workload_guidance import assess_workload_readiness, merge_follow_up_answers
from app.provision.template_mapper import recommend_from_text, recommendation_to_dict


def analyze_provision_intent(
    workload_description: str,
    follow_up_answers: Optional[Dict[str, str]] = None,
    *,
    csp: str = "AWS",
) -> Dict[str, Any]:
    """
    Analyze user intent for infrastructure provisioning (not VM pool assignment).
    """
    effective = merge_follow_up_answers(workload_description or "", follow_up_answers)
    readiness = assess_workload_readiness(effective)

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
        csp=csp,
        cluster_type=cluster_type,
        nlp_confidence=nlp_confidence,
    )

    module_keys = [m["key"] for m in recommendation.suggested_modules]
    follow_up_questions, follow_up_context = build_contextual_follow_up_questions(
        effective,
        cluster_type=cluster_type,
        module_keys=module_keys,
        csp=csp,
        follow_up_answers=follow_up_answers,
    )

    return {
        "effective_description": effective,
        "readiness": readiness,
        "follow_up_questions": follow_up_questions,
        "follow_up_context": follow_up_context,
        "nlp_confidence": nlp_confidence,
        "nlp_cluster": cluster_type.value if cluster_type else None,
        "nlp_features": nlp_features,
        "recommendation": recommendation_to_dict(recommendation),
        "auto_apply_eligible": recommendation.confidence >= 70 and readiness.get("readiness_score", 0) >= 50,
    }
