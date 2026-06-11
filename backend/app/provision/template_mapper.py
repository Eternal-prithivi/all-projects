"""Map NLP / keywords to provision templates and instance size profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional

from app.vm.models import ClusterType

STATIC_KEYWORDS = [
    "static", "website", "web site", "landing", "html", "css", "portfolio",
    "brochure", "cdn", "front-end", "frontend",
]
DB_KEYWORDS = [
    "dynamodb", "firestore", "cosmos", "nosql", "database", "mongodb",
    "postgres", "mysql", "redis", "cassandra", "data store", "serverless db",
]
BACKEND_KEYWORDS = [
    "api", "backend", "server", "compute", "microservice", "node", "python",
    "django", "flask", "fastapi", "docker", "kubernetes", "app",
]

LARGE_SCALE_PATTERNS = [
    r"\d+\s*(tb|pb)\b",
    r"\b(1000\+|10k|high traffic|heavy load)\b",
    r"\b(gpu|cuda|training|deep learning)\b",
]


@dataclass
class TemplateRecommendation:
    template: str
    size_profile: str
    confidence: int
    reasons: List[str]


def _score_keywords(text: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def recommend_from_text(
    workload_description: str,
    *,
    cluster_type: Optional[ClusterType] = None,
    nlp_confidence: int = 50,
) -> TemplateRecommendation:
    """Keyword + optional NLP cluster → template and size profile."""
    text = (workload_description or "").lower()
    reasons: List[str] = []

    static_score = _score_keywords(text, STATIC_KEYWORDS)
    db_score = _score_keywords(text, DB_KEYWORDS)
    backend_score = _score_keywords(text, BACKEND_KEYWORDS)

    if cluster_type == ClusterType.STORAGE:
        db_score += 2
        reasons.append("NLP detected storage-oriented workload")
    elif cluster_type in (ClusterType.PERFORMANCE, ClusterType.AI_ML):
        backend_score += 2
        reasons.append(f"NLP cluster: {cluster_type.value}")

    template = "backend-app"
    if static_score > backend_score and static_score >= db_score:
        template = "static-site"
        reasons.append("Static or website keywords detected")
    elif db_score > backend_score and db_score >= static_score:
        template = "serverless-db"
        reasons.append("Database or serverless data keywords detected")
    else:
        reasons.append("Application or API workload assumed")

    size_profile = "micro"
    if any(re.search(p, text) for p in LARGE_SCALE_PATTERNS):
        size_profile = "medium"
        reasons.append("Large scale or GPU signals → medium tier")
    elif cluster_type in (ClusterType.PERFORMANCE, ClusterType.AI_ML, ClusterType.MEMORY):
        size_profile = "small"
        reasons.append("Compute-heavy NLP cluster → small tier")

    confidence = min(100, max(40, nlp_confidence, static_score * 15 + db_score * 15 + backend_score * 10))

    return TemplateRecommendation(
        template=template,
        size_profile=size_profile,
        confidence=confidence,
        reasons=reasons or ["Default backend application stack"],
    )


def recommendation_to_dict(rec: TemplateRecommendation) -> dict[str, Any]:
    return {
        "template": rec.template,
        "size_profile": rec.size_profile,
        "confidence": rec.confidence,
        "reasons": rec.reasons,
    }
