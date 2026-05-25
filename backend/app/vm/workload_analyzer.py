# backend/app/vm/workload_analyzer.py
"""
Analyzes user workload descriptions and recommends optimal cluster assignment.
Phase 6: NLP pipeline (TextBlob + spaCy + tech dictionaries) with keyword fallback.
"""

import re
from typing import Dict, Tuple, List, Optional, Any

from app.vm.models import ClusterType
from app.vm.nlp_workload import analyze_workload_nlp
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class WorkloadAnalyzer:
    """
    Classifies user workloads and recommends appropriate VM clusters.
    Primary: NLP pipeline (report §4.1). Fallback: keyword matching.
    """

    GENERAL_KEYWORDS = [
        "web", "app", "application", "api", "server", "backend", "frontend",
        "compute", "cpu", "processing", "calculation", "machine learning",
        "ml", "ai", "training", "model", "analytics", "real-time",
        "service", "microservice", "container", "docker", "kubernetes",
    ]

    STORAGE_KEYWORDS = [
        "storage", "database", "db", "data", "file", "files", "backup",
        "archive", "logs", "logging", "media", "video", "image", "upload",
        "download", "transfer", "sync", "etl", "data warehouse", "big data",
        "object storage", "s3", "blob", "disk", "volume", "persistent",
    ]

    HIGH_WEIGHT_GENERAL = ["cpu-intensive", "compute-heavy", "processing", "calculation"]
    HIGH_WEIGHT_STORAGE = ["storage-heavy", "data-intensive", "large files", "terabyte"]

    @staticmethod
    def analyze(workload_description: str) -> Tuple[ClusterType, int, Dict[str, Any]]:
        """
        Analyze workload description and return recommended cluster.

        Returns:
            Tuple of (recommended_cluster, confidence_score 0-100, analysis_details)
        """
        try:
            result = analyze_workload_nlp(workload_description)
            details = dict(result.analysis_details)
            details["nlp_features"] = result.nlp_features
            return result.cluster_type, result.confidence, details
        except Exception as e:
            logger.warning(f"NLP analysis failed, using keyword fallback: {e}")
            return WorkloadAnalyzer._analyze_keywords(workload_description)

    @staticmethod
    def _analyze_keywords(workload_description: str) -> Tuple[ClusterType, int, Dict[str, Any]]:
        """Keyword fallback when NLP dependencies are unavailable."""
        if not workload_description:
            return ClusterType.GENERAL, 50, {
                "reason": "No description provided, defaulting to general cluster",
                "matched_keywords": [],
                "classifier_version": "keyword_v1",
            }

        desc_lower = workload_description.lower()
        general_score = 0
        storage_score = 0
        matched_general: List[str] = []
        matched_storage: List[str] = []

        for keyword in WorkloadAnalyzer.GENERAL_KEYWORDS:
            if keyword in desc_lower:
                weight = 2 if keyword in WorkloadAnalyzer.HIGH_WEIGHT_GENERAL else 1
                general_score += weight
                matched_general.append(keyword)

        for keyword in WorkloadAnalyzer.STORAGE_KEYWORDS:
            if keyword in desc_lower:
                weight = 2 if keyword in WorkloadAnalyzer.HIGH_WEIGHT_STORAGE else 1
                storage_score += weight
                matched_storage.append(keyword)

        if re.search(r"\d+\s*(gb|tb|pb)\s*(storage|data|files)", desc_lower):
            storage_score += 3
            matched_storage.append("large data volume pattern")

        if re.search(r"(high\s*cpu|many\s*cores|parallel\s*processing)", desc_lower):
            general_score += 3
            matched_general.append("high CPU requirement pattern")

        total_score = general_score + storage_score
        if total_score == 0:
            return ClusterType.GENERAL, 40, {
                "reason": "No clear indicators, defaulting to general cluster",
                "matched_keywords": [],
                "classifier_version": "keyword_v1",
            }

        if general_score > storage_score:
            confidence = min(100, int((general_score / total_score) * 100) + 20)
            return ClusterType.GENERAL, confidence, {
                "reason": f"General workload detected ({general_score} vs {storage_score} points)",
                "matched_keywords": matched_general,
                "score_breakdown": {"general": general_score, "storage": storage_score},
                "classifier_version": "keyword_v1",
            }
        if storage_score > general_score:
            confidence = min(100, int((storage_score / total_score) * 100) + 20)
            return ClusterType.STORAGE, confidence, {
                "reason": f"Storage workload detected ({storage_score} vs {general_score} points)",
                "matched_keywords": matched_storage,
                "score_breakdown": {"general": general_score, "storage": storage_score},
                "classifier_version": "keyword_v1",
            }

        return ClusterType.GENERAL, 50, {
            "reason": f"Equal indicators ({general_score} each), defaulting to general",
            "matched_keywords": matched_general + matched_storage,
            "classifier_version": "keyword_v1",
        }

    @staticmethod
    def get_workload_examples() -> Dict[ClusterType, List[str]]:
        return {
            ClusterType.GENERAL: [
                "Running a Node.js web application with REST API",
                "Microservices backend with Docker containers",
            ],
            ClusterType.STORAGE: [
                "File storage server with 500GB of media files",
                "Database server with large PostgreSQL instance",
                "Backup and archival system for logs",
                "Data warehouse with ETL pipelines",
                "Object storage service similar to S3",
            ],
            ClusterType.MEMORY: [
                "Redis cache with high RAM requirements",
                "In-memory analytics service with 64GB RAM",
                "Memcached session store for high concurrency",
            ],
            ClusterType.PERFORMANCE: [
                "High CPU computation for scientific simulations",
                "Parallel batch processing with many cores",
                "Low latency API service with heavy traffic",
            ],
            ClusterType.AI_ML: [
                "Machine learning model training with TensorFlow on GPU",
                "PyTorch image classification inference service",
                "XGBoost notebook pipeline for model experiments",
            ],
        }

    @staticmethod
    def validate_cluster_preference(
        workload_description: Optional[str],
        cluster_preference: Optional[ClusterType],
    ) -> Tuple[ClusterType, str]:
        if cluster_preference:
            if workload_description:
                recommended_cluster, confidence, _ = WorkloadAnalyzer.analyze(workload_description)
                if recommended_cluster != cluster_preference and confidence > 70:
                    return cluster_preference, (
                        f"Warning: Your workload seems better suited for {recommended_cluster.value} cluster "
                        f"(confidence: {confidence}%), but respecting your explicit choice of "
                        f"{cluster_preference.value}."
                    )
            return cluster_preference, ""

        if workload_description:
            recommended_cluster, confidence, _ = WorkloadAnalyzer.analyze(workload_description)
            return (
                recommended_cluster,
                f"Recommended {recommended_cluster.value} cluster based on workload analysis "
                f"(confidence: {confidence}%)",
            )

        return ClusterType.GENERAL, "No workload description provided, assigned to general cluster by default"
