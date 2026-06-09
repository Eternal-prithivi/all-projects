"""Tests for multi-signal lifecycle intelligence."""

from datetime import datetime, timedelta, timezone

from app.storage.lifecycle_signals import (
    compute_access_metrics,
    evaluate_demotion_eligibility,
    evaluate_promotion_eligibility,
    estimate_monthly_savings,
)


def _now():
    return datetime(2026, 6, 15, tzinfo=timezone.utc)


def test_compute_access_metrics_velocity_heating():
    now = _now()
    history = [now - timedelta(days=d) for d in (1, 3, 5, 40, 50)]
    file_record = {
        "access_history": history,
        "last_accessed_at": history[0],
        "access_frequency_score": 5,
        "upload_date": now - timedelta(days=90),
    }
    metrics = compute_access_metrics(file_record, now)
    assert metrics["accesses_last_7d"] >= 2
    assert metrics["is_access_heating"] is True


def test_demotion_blocked_by_recent_access():
    now = _now()
    file_record = {
        "lifecycle_policy": "auto",
        "upload_date": now - timedelta(days=60),
        "last_accessed_at": now - timedelta(days=5),
        "access_history": [now - timedelta(days=5)],
        "size_bytes": 500 * 1024 * 1024,
        "csp": "AWS",
        "storage_class": "S3 Standard",
    }
    eligible, signals = evaluate_demotion_eligibility(file_record, "warm", now)
    assert eligible is False
    assert "accessed_within_14d" in signals["blockers"]


def test_demotion_blocked_by_low_savings():
    now = _now()
    file_record = {
        "lifecycle_policy": "aggressive",
        "upload_date": now - timedelta(days=30),
        "last_accessed_at": now - timedelta(days=30),
        "size_bytes": 1024,  # 1 KB
        "csp": "AWS",
        "storage_class": "S3 Standard",
        "upload_user_intent": "archival",
    }
    eligible, signals = evaluate_demotion_eligibility(file_record, "warm", now)
    assert eligible is False
    assert "savings_below_minimum" in signals["blockers"]


def test_demotion_boosted_for_archival_intent_and_planned_tier():
    now = _now()
    file_record = {
        "lifecycle_policy": "aggressive",
        "upload_date": now - timedelta(days=30),
        "last_accessed_at": now - timedelta(days=30),
        "size_bytes": 10 * 1024 * 1024 * 1024,
        "csp": "AWS",
        "storage_class": "S3 Standard",
        "upload_user_intent": "archival",
        "initial_planned_tier": "warm",
        "tier_transition_count": 0,
    }
    eligible, signals = evaluate_demotion_eligibility(file_record, "warm", now)
    assert eligible is True
    assert "upload_intent_archival" in signals["boosts"]
    assert "matches_initial_ml_tier" in signals["boosts"]
    assert estimate_monthly_savings(file_record, "warm") > 0.08


def test_demotion_blocked_by_frequent_upload_intent():
    now = _now()
    file_record = {
        "lifecycle_policy": "auto",
        "upload_date": now - timedelta(days=40),
        "last_accessed_at": now - timedelta(days=35),
        "size_bytes": 5 * 1024 * 1024 * 1024,
        "csp": "AWS",
        "storage_class": "S3 Standard",
        "upload_user_intent": "frequent",
    }
    eligible, signals = evaluate_demotion_eligibility(file_record, "warm", now)
    assert eligible is False
    assert "upload_intent_frequent" in signals["blockers"]


def test_promotion_eligibility_uses_velocity():
    now = _now()
    heating = {
        "access_history": [now - timedelta(days=d) for d in (1, 2, 4)],
        "last_accessed_at": now - timedelta(days=1),
        "access_frequency_score": 3,
        "storage_class": "STANDARD_IA",
    }
    eligible, details = evaluate_promotion_eligibility(heating, now)
    assert eligible is True
    assert "recent_access_7d" in details["reasons"]
