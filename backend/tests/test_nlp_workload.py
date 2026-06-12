"""Tests for Phase 6 NLP workload classification."""

from app.vm.models import ClusterType
from app.vm.nlp_workload import analyze_workload_nlp
from app.vm.workload_analyzer import WorkloadAnalyzer


def test_nlp_classifies_tensorflow_as_ai_ml():
    result = analyze_workload_nlp(
        "Running TensorFlow training jobs on CIFAR-10 with GPU acceleration, need 32GB RAM"
    )
    assert result.cluster_type == ClusterType.AI_ML
    assert result.report_cluster == "ai_ml"
    assert result.confidence >= 35
    assert result.classifier_version.startswith("nlp_v1")
    assert "tensorflow" in str(result.nlp_features.get("tech_matches", {})).lower()


def test_nlp_classifies_postgres_database():
    result = analyze_workload_nlp(
        "Need PostgreSQL database with high concurrent connections and nightly backups"
    )
    assert result.cluster_type == ClusterType.DATABASE
    assert result.confidence >= 35


def test_nlp_classifies_network_gateway():
    result = analyze_workload_nlp(
        "Deploy API gateway with reverse proxy and load balancer for streaming ingress"
    )
    assert result.cluster_type == ClusterType.NETWORK
    assert result.confidence >= 25


def test_negation_without_gpu_does_not_force_ai_ml():
    result = analyze_workload_nlp("Web application without GPU requirements for simple API hosting")
    assert result.report_cluster != "ai_ml" or "gpu" in result.nlp_features.get("negated_terms", [])


def test_workload_analyzer_returns_nlp_version():
    cluster, confidence, details = WorkloadAnalyzer.analyze(
        "Deploy microservices with Docker and MongoDB replica sets"
    )
    assert cluster in (
        ClusterType.GENERAL,
        ClusterType.STORAGE,
        ClusterType.DATABASE,
    )
    assert confidence > 0
    assert details.get("classifier_version") == "keyword_v1" or details.get("classifier_version", "").startswith("nlp_v1")


def test_empty_description_defaults_general():
    cluster, confidence, details = WorkloadAnalyzer.analyze("")
    assert cluster == ClusterType.GENERAL
    assert confidence == 50
