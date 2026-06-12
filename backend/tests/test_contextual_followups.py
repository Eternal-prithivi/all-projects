"""Tests for intent-aware contextual follow-up questions."""

from app.provision.intent_analyzer import analyze_provision_intent
from app.vm.contextual_followups import build_contextual_follow_up_questions
from app.vm.models import ClusterType


def test_s3_storage_asks_region_and_volume_not_generic_environment():
    text = "I need an s3 bucket for file storage"
    questions, ctx = build_contextual_follow_up_questions(
        text,
        cluster_type=ClusterType.STORAGE,
        module_keys=["s3"],
        csp="AWS",
    )
    assert ctx["kind"] == "storage"
    qids = [q["id"] for q in questions]
    assert "storage_region" in qids
    assert "storage_volume" in qids
    assert "environment" not in qids
    assert "data_scale" not in qids
    assert all("region" in q["question"].lower() or "data" in q["question"].lower() or "used" in q["question"].lower()
               or "production" in q["question"].lower() for q in questions)


def test_storage_with_region_skips_region_question():
    text = "S3 bucket in ap-south-1 for 20GB of team files"
    questions, _ = build_contextual_follow_up_questions(
        text,
        cluster_type=ClusterType.STORAGE,
        module_keys=["s3"],
        csp="AWS",
    )
    assert all(q["id"] != "storage_region" for q in questions)


def test_api_workload_asks_traffic_not_storage_volume():
    text = "Node.js REST API for my startup"
    questions, ctx = build_contextual_follow_up_questions(
        text,
        cluster_type=ClusterType.GENERAL,
        module_keys=["ec2", "vpc"],
        csp="AWS",
    )
    assert ctx["kind"] == "compute"
    qids = [q["id"] for q in questions]
    assert "compute_traffic" in qids or "compute_region" in qids


def test_provision_intent_api_includes_contextual_followups():
    result = analyze_provision_intent("I need a s3 bucket for file storage", None, csp="AWS")
    assert result["follow_up_context"]["kind"] == "storage"
    assert len(result["follow_up_questions"]) >= 1
    assert result["follow_up_questions"][0]["id"].startswith("storage_")
