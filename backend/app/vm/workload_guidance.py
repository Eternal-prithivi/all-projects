"""
Workload description readiness and guided follow-up questions (report §4.1 UX).

Helps users see how complete their prompt is before VM assignment and which
signals the NLP pipeline still needs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.ml.acceptance import NLP_AUTO_ASSIGN_CONFIDENCE, NLP_MIN_WORD_COUNT_FOR_TRAINING
from app.vm.nlp_workload import TECH_DICTIONARIES, _match_tech_dictionary, _tokenize

# Signals that improve NLP classification quality
READINESS_SIGNALS: Dict[str, Dict[str, Any]] = {
    "workload_type": {
        "label": "Workload type",
        "hint": "Mention web app, API, database, ML, backup, or batch job",
        "patterns": [
            r"\b(web|website|api|rest|graphql|service|app|application)\b",
            r"\b(database|db|sql|nosql|warehouse|etl)\b",
            r"\b(machine learning|ml|ai|training|inference|model)\b",
            r"\b(backup|archive|file|object storage|media)\b",
            r"\b(batch|cron|scheduled|pipeline)\b",
        ],
    },
    "technology": {
        "label": "Technologies",
        "hint": "Name frameworks or tools (e.g. PostgreSQL, Docker, TensorFlow)",
        "tech_categories": list(TECH_DICTIONARIES.keys()),
    },
    "data_scale": {
        "label": "Data or resource scale",
        "hint": "Include size or load (e.g. 500GB, 10TB, high CPU, 1000 users)",
        "patterns": [
            r"\d+\s*(gb|tb|pb|mb)\b",
            r"\b(high\s*cpu|many\s*cores|ram|memory|concurrent|users|qps|rps)\b",
            r"\b(large|small|heavy|light)\s+(files?|data|dataset|workload)\b",
        ],
    },
    "environment": {
        "label": "Environment / priority",
        "hint": "Note production vs dev, urgency, or SLA needs",
        "patterns": [
            r"\b(production|prod|staging|dev|test|demo)\b",
            r"\b(urgent|critical|high priority|24/7|sla)\b",
        ],
    },
}

FOLLOW_UP_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "workload_type": {
        "question": "What best describes this workload?",
        "options": [
            "Web or API service",
            "Database or data store",
            "Machine learning / AI training",
            "File storage or backups",
            "Batch / ETL processing",
        ],
    },
    "technology": {
        "question": "Which technologies will you use?",
        "options": [
            "PostgreSQL or MySQL",
            "MongoDB or Redis",
            "Docker / Kubernetes",
            "TensorFlow / PyTorch",
            "Object storage (S3/GCS/Azure)",
            "Not sure yet",
        ],
    },
    "data_scale": {
        "question": "What scale or resources do you expect?",
        "options": [
            "Under 50GB data",
            "50GB–1TB data",
            "Over 1TB data",
            "High CPU / compute intensive",
            "Low traffic / small team",
        ],
    },
    "environment": {
        "question": "What environment is this for?",
        "options": [
            "Production (high availability)",
            "Staging / testing",
            "Development only",
            "Urgent / time-sensitive",
        ],
    },
}

READINESS_LABELS: List[Tuple[int, str]] = [
    (85, "Ready for auto-assignment"),
    (70, "Strong — NLP can recommend confidently"),
    (50, "Fair — add a few details below"),
    (25, "Weak — describe workload type and tools"),
    (0, "Too vague — answer the questions below"),
]


def merge_follow_up_answers(
    workload_description: str,
    follow_up_answers: Optional[Dict[str, str]] = None,
) -> str:
    """Combine free-text description with structured follow-up answers for NLP."""
    base = (workload_description or "").strip()
    if not follow_up_answers:
        return base

    extras: List[str] = []
    for signal_id, answer in follow_up_answers.items():
        if not answer or not str(answer).strip():
            continue
        label = READINESS_SIGNALS.get(signal_id, {}).get("label", signal_id.replace("_", " "))
        extras.append(f"{label}: {str(answer).strip()}")

    if not extras:
        return base
    if not base:
        return ". ".join(extras)
    return f"{base}. {' '.join(extras)}"


def _signal_present(signal_id: str, text: str, tech_matches: Dict[str, List[str]]) -> bool:
    spec = READINESS_SIGNALS[signal_id]
    lower = text.lower()

    if signal_id == "technology":
        if tech_matches:
            return True
        for category in spec.get("tech_categories", []):
            for term in TECH_DICTIONARIES.get(category, []):
                if term in lower:
                    return True
        return False

    for pattern in spec.get("patterns", []):
        if re.search(pattern, lower, re.IGNORECASE):
            return True
    return False


def assess_workload_readiness(workload_description: str) -> Dict[str, Any]:
    """
    Score how complete a workload description is for NLP (0–100), independent of
    cluster confidence.
    """
    text = (workload_description or "").strip()
    tokens = _tokenize(text)
    word_count = len(tokens)
    tech_matches = _match_tech_dictionary(text) if text else {}

    matched_signals: List[str] = []
    missing_signals: List[Dict[str, str]] = []

    for signal_id, spec in READINESS_SIGNALS.items():
        if _signal_present(signal_id, text, tech_matches):
            matched_signals.append(signal_id)
        else:
            missing_signals.append(
                {
                    "id": signal_id,
                    "label": spec["label"],
                    "hint": spec["hint"],
                }
            )

    # Weighted readiness (max 100)
    score = 0
    score += min(25, word_count * 2)  # up to ~12 words for full word points
    score += len(matched_signals) * 18  # up to 72 for all four signals
    if tech_matches:
        score += min(15, sum(len(v) for v in tech_matches.values()) * 3)
    if re.search(r"\d+\s*(gb|tb|pb|mb)", text.lower()):
        score += 8

    readiness_score = int(min(100, max(0, score)))
    readiness_label = READINESS_LABELS[-1][1]
    for threshold, label in READINESS_LABELS:
        if readiness_score >= threshold:
            readiness_label = label
            break

    min_words = NLP_MIN_WORD_COUNT_FOR_TRAINING
    auto_assign_threshold = int(NLP_AUTO_ASSIGN_CONFIDENCE * 100)

    return {
        "readiness_score": readiness_score,
        "readiness_label": readiness_label,
        "word_count": word_count,
        "min_recommended_words": min_words,
        "matched_signals": [
            {"id": sid, "label": READINESS_SIGNALS[sid]["label"]} for sid in matched_signals
        ],
        "missing_signals": missing_signals,
        "matched_keywords": [t for terms in tech_matches.values() for t in terms],
        "auto_assign_confidence_threshold": auto_assign_threshold,
        "is_ready_for_analysis": readiness_score >= 50 and word_count >= 5,
    }


def build_follow_up_questions(
    missing_signals: List[Dict[str, str]],
    follow_up_answers: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Return up to 3 guided questions for missing signals."""
    answers = follow_up_answers or {}
    questions: List[Dict[str, Any]] = []

    for item in missing_signals[:3]:
        signal_id = item["id"]
        template = FOLLOW_UP_TEMPLATES.get(signal_id)
        if not template:
            continue
        current = answers.get(signal_id, "")
        questions.append(
            {
                "id": signal_id,
                "question": template["question"],
                "options": template["options"],
                "hint": item.get("hint", ""),
                "answered": bool(current and str(current).strip()),
                "current_answer": current or None,
            }
        )
    return questions
