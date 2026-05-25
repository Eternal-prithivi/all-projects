"""Tests for workload readiness guidance."""

from app.vm.workload_guidance import (
    assess_workload_readiness,
    build_follow_up_questions,
    merge_follow_up_answers,
)


def test_empty_description_low_readiness():
    result = assess_workload_readiness("")
    assert result["readiness_score"] < 30
    assert len(result["missing_signals"]) == 4


def test_rich_description_high_readiness():
    text = (
        "Production PostgreSQL database on Docker with 500GB storage, "
        "high CPU for concurrent API traffic, nightly backups to S3"
    )
    result = assess_workload_readiness(text)
    assert result["readiness_score"] >= 70
    assert result["is_ready_for_analysis"] is True
    assert len(result["missing_signals"]) <= 1


def test_follow_up_questions_for_missing_signals():
    readiness = assess_workload_readiness("hello")
    questions = build_follow_up_questions(readiness["missing_signals"])
    assert len(questions) >= 1
    assert "question" in questions[0]
    assert len(questions[0]["options"]) >= 2


def test_merge_follow_up_answers():
    merged = merge_follow_up_answers(
        "Need a VM",
        {"workload_type": "Database or data store", "data_scale": "500GB–1TB data"},
    )
    assert "Database" in merged
    assert "500GB" in merged or "1TB" in merged
