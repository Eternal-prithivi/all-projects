# =============================================================================
# MODULE: vm/nlp_workload.py  (464 lines)
# PURPOSE: NLP workload classification — maps free-text workload descriptions to
#          one of the five cluster types (GENERAL/STORAGE/MEMORY/PERFORMANCE/AI_ML)
# PIPELINE: sentiment + urgency scoring → spaCy NER + tech dictionaries → synonym expansion
#           → keyword matching → cluster confidence scores → top cluster assigned
# CALLED BY: routes_vm.py → POST /api/vm/analyze-workload (and during /request)
# DEPENDS ON: spaCy (en_core_web_sm), workload_analyzer.py, workload_guidance.py
# DO NOT:
#   - Change the five output cluster names — routes_vm.py and manager.py hard-wire them
#   - Remove the confidence threshold — low-confidence descriptions fall back to GENERAL
#   - Add synchronous spaCy loads inside request handlers — model loads at startup only
# =============================================================================
"""
→ contextual weighting → negation handling → cluster scoring → confidence boost.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.ml.inference import WORKLOAD_CLASSIFIER_ARTIFACT, load_workload_classifier_artifact
from app.ml.acceptance import (
    NLP_AUTO_ASSIGN_CONFIDENCE,
    NLP_CONFIDENCE_BOOST_MAX,
    NLP_CONFIDENCE_BOOST_MIN,
)
from app.utils.logger import setup_logger
from app.vm.models import ClusterType

logger = setup_logger(__name__)

URGENCY_KEYWORDS = [
    "urgent",
    "immediately",
    "asap",
    "critical",
    "high priority",
    "production",
    "as soon as possible",
]

NEGATION_PATTERNS = [
    r"\bnot\s+\w+",
    r"\bdon'?t\s+\w+",
    r"\bwithout\s+\w+",
    r"\bno\s+need\b",
    r"\bnever\s+use\b",
]

TECH_DICTIONARIES: Dict[str, List[str]] = {
    "database": [
        "postgresql",
        "postgres",
        "mongodb",
        "mysql",
        "redis",
        "cassandra",
        "mariadb",
        "dynamodb",
        "sql server",
        "database",
        "db",
        "rdbms",
    ],
    "framework": [
        "django",
        "react",
        "tensorflow",
        "spring boot",
        "flask",
        "fastapi",
        "node.js",
        "nodejs",
        "express",
    ],
    "ml_tool": [
        "scikit-learn",
        "sklearn",
        "pytorch",
        "keras",
        "xgboost",
        "pandas",
        "numpy",
        "jupyter",
        "neural network",
        "deep learning",
        "gpu",
        "cuda",
    ],
    "container": ["docker", "kubernetes", "k8s", "podman", "openshift", "container", "microservice"],
    "storage_system": [
        "s3",
        "gcs",
        "google cloud storage",
        "azure blob",
        "hdfs",
        "ceph",
        "object storage",
        "blob storage",
        "nfs",
    ],
}

# Report cluster → signal weights when a category is detected
CATEGORY_CLUSTER_WEIGHTS: Dict[str, Dict[str, float]] = {
    "database": {"storage": 2.0, "memory": 1.0},
    "framework": {"general": 1.5, "performance": 1.0},
    "ml_tool": {"ai_ml": 3.0, "performance": 1.5, "general": 1.0},
    "container": {"general": 1.5, "performance": 1.0},
    "storage_system": {"storage": 3.0},
}

SYNONYM_MAP: Dict[str, List[str]] = {
    "database": ["db", "datastore", "data store", "rdbms", "sql"],
    "storage": ["disk", "files", "object store", "backup"],
    "gpu": ["graphics", "cuda", "accelerator"],
    "web": ["website", "http", "api", "rest"],
}

REPORT_CLUSTERS = ("general", "storage", "memory", "performance", "ai_ml")


@dataclass
class NLPWorkloadResult:
    cluster_type: ClusterType
    confidence: int
    report_cluster: str
    auto_assign_eligible: bool
    classifier_version: str
    nlp_features: Dict[str, Any] = field(default_factory=dict)
    analysis_details: Dict[str, Any] = field(default_factory=dict)


def _load_textblob():
    try:
        from textblob import TextBlob

        return TextBlob
    except ImportError:
        return None


def _load_spacy():
    try:
        import spacy

        return spacy.load("en_core_web_sm")
    except Exception as e:
        logger.warning(f"spaCy model unavailable ({e}); using dictionary NER only")
        return None


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _extract_sentiment_and_urgency(text: str) -> Dict[str, Any]:
    polarity = 0.0
    subjectivity = 0.0
    TextBlob = _load_textblob()
    if TextBlob and text.strip():
        blob = TextBlob(text)
        polarity = float(blob.sentiment.polarity)
        subjectivity = float(blob.sentiment.subjectivity)

    urgency_level = 0
    lower = text.lower()
    for kw in URGENCY_KEYWORDS:
        if kw in lower:
            urgency_level = min(5, urgency_level + 1)

    return {
        "sentiment_polarity": round(polarity, 3),
        "sentiment_subjectivity": round(subjectivity, 3),
        "urgency_level": urgency_level,
    }


def _match_tech_dictionary(text: str) -> Dict[str, List[str]]:
    lower = text.lower()
    matches: Dict[str, List[str]] = {cat: [] for cat in TECH_DICTIONARIES}
    for category, terms in TECH_DICTIONARIES.items():
        for term in terms:
            if term in lower:
                matches[category].append(term)
    return {k: v for k, v in matches.items() if v}


def _extract_spacy_entities(text: str, nlp: Any) -> List[Dict[str, str]]:
    entities: List[Dict[str, str]] = []
    if not nlp or not text.strip():
        return entities
    doc = nlp(text)
    for ent in doc.ents:
        entities.append({"text": ent.text, "label": ent.label_})
    return entities


def _expand_keywords(tokens: List[str]) -> Set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        for base, synonyms in SYNONYM_MAP.items():
            if token == base or token in synonyms:
                expanded.add(base)
                expanded.update(synonyms)
    return expanded


def _contextual_keyword_weights(text: str, keywords: Set[str]) -> Dict[str, float]:
    """First sentence 1.5x; sentence-start token 1.3x; ALL CAPS emphasis 1.2x."""
    weights: Dict[str, float] = {kw: 1.0 for kw in keywords}
    if not text.strip():
        return weights

    sentences = re.split(r"[.!?]\s+", text.strip())
    first_sentence = sentences[0].lower() if sentences else text.lower()

    for kw in keywords:
        if kw in first_sentence:
            weights[kw] = weights.get(kw, 1.0) * 1.5

    for match in re.finditer(r"(?:^|[.!?]\s+)(\w+)", text):
        word = match.group(1).lower()
        if word in keywords:
            weights[word] = weights.get(word, 1.0) * 1.3

    for match in re.finditer(r"\b[A-Z]{2,}\b", text):
        token = match.group(0).lower()
        if token in keywords or token in {k for ks in SYNONYM_MAP.values() for k in ks}:
            for kw in keywords:
                if kw == token or token in SYNONYM_MAP.get(kw, []):
                    weights[kw] = weights.get(kw, 1.0) * 1.2

    return weights


def _detect_negated_terms(text: str, terms: List[str]) -> Set[str]:
    negated: Set[str] = set()
    lower = text.lower()
    for term in terms:
        for pattern in NEGATION_PATTERNS:
            for match in re.finditer(pattern, lower):
                start = max(0, match.start() - 40)
                end = min(len(lower), match.end() + 40)
                window = lower[start:end]
                if term in window:
                    negated.add(term)
                    break
    return negated


def _score_report_clusters(
    text: str,
    tech_matches: Dict[str, List[str]],
    negated: Set[str],
    contextual_weights: Dict[str, float],
) -> Dict[str, float]:
    scores = {c: 0.0 for c in REPORT_CLUSTERS}
    lower = text.lower()

    for category, terms in tech_matches.items():
        for term in terms:
            if term in negated:
                continue
            w = contextual_weights.get(term, 1.0)
            for cluster, boost in CATEGORY_CLUSTER_WEIGHTS.get(category, {}).items():
                scores[cluster] = scores.get(cluster, 0.0) + boost * w

    # Heuristic patterns (report examples)
    if re.search(r"\d+\s*(gb|tb|pb)\s*(storage|data|files)", lower):
        scores["storage"] += 3.0
    if re.search(r"(high\s*cpu|many\s*cores|parallel\s*processing|compute)", lower):
        scores["performance"] += 2.5
        scores["general"] += 1.0
    if re.search(r"(tensorflow|pytorch|training|inference|gpu)", lower) and "gpu" not in negated:
        scores["ai_ml"] += 3.0
    if re.search(r"(redis|memcached|in-memory|ram|memory)", lower):
        if not any(t in negated for t in ("redis", "memory", "ram")):
            scores["memory"] += 2.0

    tokens = _expand_keywords(_tokenize(text))
    keyword_cluster_map = {
        "web": "general",
        "api": "general",
        "database": "storage",
        "storage": "storage",
        "backup": "storage",
        "gpu": "ai_ml",
        "cuda": "ai_ml",
    }
    for token in tokens:
        if token in negated:
            continue
        cluster = keyword_cluster_map.get(token)
        if cluster:
            scores[cluster] += 1.0 * contextual_weights.get(token, 1.0)

    return scores


def _score_trained_workload_model(text: str, negated: Set[str]) -> Dict[str, Any]:
    artifact = load_workload_classifier_artifact()
    if not artifact:
        return {
            "available": False,
            "artifact_path": None,
        }

    pipeline = artifact.get("pipeline")
    if pipeline is None:
        return {
            "available": False,
            "artifact_path": str(WORKLOAD_CLASSIFIER_ARTIFACT),
            "error": "pipeline_missing",
        }

    try:
        predicted_cluster = str(pipeline.predict([text])[0])
        probabilities: Dict[str, float] = {}
        confidence = 0.0
        if hasattr(pipeline, "predict_proba"):
            proba = pipeline.predict_proba([text])[0]
            labels = list(getattr(pipeline, "classes_", []))
            probabilities = {str(label): round(float(prob), 4) for label, prob in zip(labels, proba)}
            confidence = max(probabilities.values()) if probabilities else 0.0

        if predicted_cluster == "ai_ml" and any(term in negated for term in ("gpu", "cuda", "training")):
            return {
                "available": True,
                "applied": False,
                "predicted_cluster": predicted_cluster,
                "confidence": confidence,
                "probabilities": probabilities,
                "reason": "trained model AI/ML signal suppressed by negation",
                "artifact_path": str(WORKLOAD_CLASSIFIER_ARTIFACT),
                "model_version": artifact.get("model_version"),
                "training_samples": artifact.get("training_samples"),
                "test_accuracy": artifact.get("test_accuracy"),
            }

        return {
            "available": True,
            "applied": predicted_cluster in REPORT_CLUSTERS,
            "predicted_cluster": predicted_cluster,
            "confidence": round(float(confidence), 4),
            "probabilities": probabilities,
            "artifact_path": str(WORKLOAD_CLASSIFIER_ARTIFACT),
            "model_version": artifact.get("model_version"),
            "training_samples": artifact.get("training_samples"),
            "test_accuracy": artifact.get("test_accuracy"),
        }
    except Exception as exc:
        logger.warning(f"Workload classifier artifact failed during inference: {exc}")
        return {
            "available": False,
            "artifact_path": str(WORKLOAD_CLASSIFIER_ARTIFACT),
            "error": str(exc),
        }


def _map_report_cluster_to_type(report_cluster: str) -> ClusterType:
    """Map report taxonomy directly to deployable VM pools."""
    mapping = {
        "general": ClusterType.GENERAL,
        "storage": ClusterType.STORAGE,
        "memory": ClusterType.MEMORY,
        "performance": ClusterType.PERFORMANCE,
        "ai_ml": ClusterType.AI_ML,
    }
    return mapping.get(report_cluster, ClusterType.GENERAL)


def _compute_confidence_boost(
    sentiment: Dict[str, Any],
    tech_matches: Dict[str, List[str]],
    negated: Set[str],
    entity_count: int,
) -> float:
    boost = 0.0
    entity_total = sum(len(v) for v in tech_matches.values())
    if entity_total >= 3:
        boost += 0.08
    if entity_count >= 2:
        boost += 0.04
    if sentiment.get("urgency_level", 0) >= 2:
        boost += 0.05
    if len(negated) > 0:
        boost -= 0.06
    if sentiment.get("sentiment_polarity", 0) < -0.2:
        boost += 0.03  # production-critical tone
    return max(NLP_CONFIDENCE_BOOST_MIN, min(NLP_CONFIDENCE_BOOST_MAX, boost))


def analyze_workload_nlp(workload_description: str) -> NLPWorkloadResult:
    """
    Full NLP pipeline for workload description (report §4.1).
    """
    if not workload_description or not workload_description.strip():
        return NLPWorkloadResult(
            cluster_type=ClusterType.GENERAL,
            confidence=50,
            report_cluster="general",
            auto_assign_eligible=False,
            classifier_version="nlp_v1",
            nlp_features={},
            analysis_details={
                "reason": "No description provided, defaulting to general cluster",
                "matched_keywords": [],
            },
        )

    text = workload_description.strip()
    sentiment = _extract_sentiment_and_urgency(text)
    nlp = _load_spacy()
    spacy_entities = _extract_spacy_entities(text, nlp)
    tech_matches = _match_tech_dictionary(text)

    all_terms = [t for terms in tech_matches.values() for t in terms]
    negated = _detect_negated_terms(text, all_terms)
    tokens = list(_expand_keywords(_tokenize(text)))
    contextual_weights = _contextual_keyword_weights(text, set(tokens))

    cluster_scores = _score_report_clusters(text, tech_matches, negated, contextual_weights)
    trained_model_signal = _score_trained_workload_model(text, negated)
    if trained_model_signal.get("applied"):
        predicted_cluster = trained_model_signal.get("predicted_cluster")
        confidence = float(trained_model_signal.get("confidence", 0.0) or 0.0)
        cluster_scores[str(predicted_cluster)] += max(confidence, 0.35) * 2.5

    total = sum(cluster_scores.values()) or 1.0
    report_cluster = max(cluster_scores, key=cluster_scores.get)
    cluster_type = _map_report_cluster_to_type(report_cluster)

    base_confidence = int((cluster_scores[report_cluster] / total) * 70) + 25
    boost = _compute_confidence_boost(sentiment, tech_matches, negated, len(spacy_entities))
    confidence = int(min(100, max(35, base_confidence + boost * 100)))
    auto_assign = confidence >= int(NLP_AUTO_ASSIGN_CONFIDENCE * 100)

    nlp_features = {
        **sentiment,
        "tech_matches": tech_matches,
        "spacy_entities": spacy_entities,
        "negated_terms": sorted(negated),
        "cluster_scores": {k: round(v, 2) for k, v in cluster_scores.items()},
        "trained_model": trained_model_signal,
        "confidence_boost": round(boost, 3),
        "word_count": len(_tokenize(text)),
    }

    matched = [t for terms in tech_matches.values() for t in terms if t not in negated]
    analysis_details = {
        "reason": (
            f"NLP classified as {report_cluster} cluster "
            f"(deployed pool: {cluster_type.value}, score {cluster_scores[report_cluster]:.1f})"
        ),
        "matched_keywords": matched,
        "report_cluster": report_cluster,
        "score_breakdown": cluster_scores,
        "classifier_version": "nlp_v1+sample_text_model" if trained_model_signal.get("applied") else "nlp_v1",
        "auto_assign_eligible": auto_assign,
    }

    return NLPWorkloadResult(
        cluster_type=cluster_type,
        confidence=confidence,
        report_cluster=report_cluster,
        auto_assign_eligible=auto_assign,
        classifier_version="nlp_v1+sample_text_model" if trained_model_signal.get("applied") else "nlp_v1",
        nlp_features=nlp_features,
        analysis_details=analysis_details,
    )
