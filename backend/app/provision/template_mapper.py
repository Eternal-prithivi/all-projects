"""Map NLP / keywords to provision templates, modules, and size profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.provision.module_mapper import recommend_modules, template_from_module_flags
from app.vm.models import ClusterType

STATIC_KEYWORDS = [
    "static", "website", "web site", "landing", "html", "css", "portfolio",
    "brochure", "cdn", "front-end", "frontend",
]
STORAGE_KEYWORDS = [
    "s3", "bucket", "gcs", "blob", "object storage", "file storage",
    "store files", "upload", "backup files", "archival",
]
DB_KEYWORDS = [
    "dynamodb", "firestore", "cosmos", "nosql", "database", "mongodb",
    "postgres", "mysql", "redis", "cassandra", "serverless db",
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
    suggested_modules: List[dict[str, Any]] = field(default_factory=list)
    module_flags: Dict[str, bool] = field(default_factory=dict)
    module_reasons: Dict[str, str] = field(default_factory=dict)


def _score_keywords(text: str, keywords: List[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def recommend_from_text(
    workload_description: str,
    *,
    csp: str = "AWS",
    cluster_type: Optional[ClusterType] = None,
    nlp_confidence: int = 50,
) -> TemplateRecommendation:
    """Keyword + NLP cluster → template, size profile, and per-module flags."""
    text = (workload_description or "").lower()
    reasons: List[str] = []

    module_rec = recommend_modules(
        workload_description,
        csp=csp,
        cluster_type=cluster_type,
    )
    template = template_from_module_flags(csp, module_rec.module_flags)

    static_score = _score_keywords(text, STATIC_KEYWORDS)
    storage_score = _score_keywords(text, STORAGE_KEYWORDS)
    db_score = _score_keywords(text, DB_KEYWORDS)
    backend_score = _score_keywords(text, BACKEND_KEYWORDS)

    if cluster_type == ClusterType.STORAGE:
        storage_score += 3
        reasons.append("NLP detected storage-oriented workload")
    elif cluster_type in (ClusterType.PERFORMANCE, ClusterType.AI_ML):
        backend_score += 2
        reasons.append(f"NLP cluster: {cluster_type.value}")

    # Fallback template scoring when module mapper returns empty
    if not module_rec.suggested_modules:
        if static_score > backend_score and static_score >= db_score:
            template = "static-site"
            reasons.append("Static or website keywords detected")
        elif db_score > backend_score and db_score >= static_score:
            template = "serverless-db"
            reasons.append("Database keywords detected")
        else:
            template = "backend-app"
            reasons.append("Application or API workload assumed")
    elif template == "static-site":
        reasons.append("Object storage module recommended")
    elif template == "serverless-db":
        reasons.append("Database module recommended")
    elif template == "backend-app":
        reasons.append("Compute / network modules recommended")
    else:
        reasons.append("Custom module mix from your description")

    if storage_score and template == "static-site":
        reasons.append("Storage keywords matched (S3 / GCS / Blob)")

    size_profile = "micro"
    if any(re.search(p, text) for p in LARGE_SCALE_PATTERNS):
        size_profile = "medium"
        reasons.append("Large scale or GPU signals → medium tier")
    elif cluster_type in (ClusterType.PERFORMANCE, ClusterType.AI_ML, ClusterType.MEMORY):
        size_profile = "small"
        reasons.append("Compute-heavy NLP cluster → small tier")

    module_bonus = len(module_rec.suggested_modules) * 5
    confidence = min(
        100,
        max(40, nlp_confidence, static_score * 15 + storage_score * 12 + db_score * 15 + backend_score * 10 + module_bonus),
    )

    return TemplateRecommendation(
        template=template,
        size_profile=size_profile,
        confidence=confidence,
        reasons=reasons or ["Default backend application stack"],
        suggested_modules=module_rec.suggested_modules,
        module_flags=module_rec.module_flags,
        module_reasons=module_rec.module_reasons,
    )


def recommendation_to_dict(rec: TemplateRecommendation) -> dict[str, Any]:
    out = {
        "template": rec.template,
        "size_profile": rec.size_profile,
        "confidence": rec.confidence,
        "reasons": rec.reasons,
    }
    out["suggested_modules"] = rec.suggested_modules
    out["module_flags"] = rec.module_flags
    out["module_reasons"] = rec.module_reasons
    return out
