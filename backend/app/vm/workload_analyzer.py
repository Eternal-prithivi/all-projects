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

    DATABASE_KEYWORDS = [
        "database", "db", "postgres", "postgresql", "mysql", "mariadb",
        "mongodb", "redis", "cassandra", "dynamodb", "oltp", "sql",
        "replica", "replication", "transaction", "acid", "nosql",
        "connection pool", "concurrent connections", "backup",
    ]

    NETWORK_KEYWORDS = [
        "network", "proxy", "gateway", "ingress", "load balancer", "lb",
        "streaming", "cdn", "vpn", "firewall", "routing", "nat",
        "websocket", "grpc", "api gateway", "reverse proxy",
    ]

    MEMORY_KEYWORDS = [
        "memory", "ram", "cache", "redis", "memcached", "in-memory",
        "high memory", "highmem",
    ]

    PERFORMANCE_KEYWORDS = [
        "performance", "cpu-bound", "batch", "compute", "parallel",
        "high cpu", "scientific", "simulation", "rendering",
    ]

    AI_ML_KEYWORDS = [
        "tensorflow", "pytorch", "gpu", "cuda", "inference", "training",
        "machine learning", "deep learning", "neural", "xgboost",
    ]

    HIGH_WEIGHT_GENERAL = ["cpu-intensive", "compute-heavy", "processing", "calculation"]
    HIGH_WEIGHT_STORAGE = ["storage-heavy", "data-intensive", "large files", "terabyte"]
    HIGH_WEIGHT_DATABASE = ["postgresql", "mysql", "oltp", "replica set"]
    HIGH_WEIGHT_NETWORK = ["load balancer", "api gateway", "reverse proxy"]
    HIGH_WEIGHT_MEMORY = ["in-memory", "high memory", "redis cache"]
    HIGH_WEIGHT_PERFORMANCE = ["cpu-bound", "batch processing", "high cpu"]
    HIGH_WEIGHT_AI_ML = ["gpu", "tensorflow", "pytorch", "training"]

    CLUSTER_KEYWORD_MAP = {
        ClusterType.GENERAL: ("GENERAL_KEYWORDS", "HIGH_WEIGHT_GENERAL"),
        ClusterType.STORAGE: ("STORAGE_KEYWORDS", "HIGH_WEIGHT_STORAGE"),
        ClusterType.DATABASE: ("DATABASE_KEYWORDS", "HIGH_WEIGHT_DATABASE"),
        ClusterType.NETWORK: ("NETWORK_KEYWORDS", "HIGH_WEIGHT_NETWORK"),
        ClusterType.MEMORY: ("MEMORY_KEYWORDS", "HIGH_WEIGHT_MEMORY"),
        ClusterType.PERFORMANCE: ("PERFORMANCE_KEYWORDS", "HIGH_WEIGHT_PERFORMANCE"),
        ClusterType.AI_ML: ("AI_ML_KEYWORDS", "HIGH_WEIGHT_AI_ML"),
    }

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
        scores: Dict[ClusterType, int] = {ct: 0 for ct in WorkloadAnalyzer.CLUSTER_KEYWORD_MAP}
        matched: Dict[ClusterType, List[str]] = {ct: [] for ct in WorkloadAnalyzer.CLUSTER_KEYWORD_MAP}

        for cluster_type, (kw_attr, high_attr) in WorkloadAnalyzer.CLUSTER_KEYWORD_MAP.items():
            keywords = getattr(WorkloadAnalyzer, kw_attr)
            high_weight = getattr(WorkloadAnalyzer, high_attr)
            for keyword in keywords:
                if keyword in desc_lower:
                    weight = 2 if keyword in high_weight else 1
                    scores[cluster_type] += weight
                    matched[cluster_type].append(keyword)

        if re.search(r"\d+\s*(gb|tb|pb)\s*(storage|data|files)", desc_lower):
            scores[ClusterType.STORAGE] += 3
            matched[ClusterType.STORAGE].append("large data volume pattern")

        if re.search(r"(high\s*cpu|many\s*cores|parallel\s*processing)", desc_lower):
            scores[ClusterType.PERFORMANCE] += 3
            matched[ClusterType.PERFORMANCE].append("high CPU requirement pattern")

        if re.search(r"(\d+\s*gb\s*ram|high\s*memory|in-memory)", desc_lower):
            scores[ClusterType.MEMORY] += 3
            matched[ClusterType.MEMORY].append("high memory pattern")

        total_score = sum(scores.values())
        if total_score == 0:
            return ClusterType.GENERAL, 40, {
                "reason": "No clear indicators, defaulting to general cluster",
                "matched_keywords": [],
                "classifier_version": "keyword_v1",
            }

        best = max(scores, key=scores.get)
        best_score = scores[best]
        if list(scores.values()).count(best_score) > 1:
            return ClusterType.GENERAL, 50, {
                "reason": "Equal indicators across clusters, defaulting to general",
                "matched_keywords": matched[best],
                "score_breakdown": {k.value: v for k, v in scores.items()},
                "classifier_version": "keyword_v1",
            }

        confidence = min(100, int((best_score / total_score) * 100) + 20)
        return best, confidence, {
            "reason": f"{best.value} workload detected (score {best_score}/{total_score})",
            "matched_keywords": matched[best],
            "score_breakdown": {k.value: v for k, v in scores.items()},
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
            ClusterType.DATABASE: [
                "PostgreSQL OLTP with nightly backups",
                "MySQL replica set with connection pooling",
            ],
            ClusterType.NETWORK: [
                "API gateway with reverse proxy and load balancing",
                "Streaming ingress with WebSocket connections",
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
