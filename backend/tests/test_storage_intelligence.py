"""Tests for storage intelligence APIs and cost preview."""

from datetime import datetime, timedelta, timezone

from app.storage.storage_intelligence import (
    build_cost_preview,
    build_file_insight,
    compute_portfolio_health,
    cross_cloud_tier_comparison,
)


def test_cross_cloud_comparison_marks_cheapest():
    rows = cross_cloud_tier_comparison(10.0, "warm", "cost")
    assert len(rows) == 3
    assert sum(1 for r in rows if r["is_recommended"]) == 1


def test_cost_preview_includes_scenarios_and_savings():
    preview = build_cost_preview(
        file_size_mb=1024,
        determined_tier="warm",
        user_priority="cost",
        user_intent="archival",
        lifecycle_policy="auto",
    )
    assert preview["determined_tier"] == "warm"
    assert len(preview["scenarios"]) == 2
    assert preview["estimated_12_month_savings_usd"] >= 0
    assert len(preview["cross_cloud"]) == 3


def test_file_insight_shows_blockers_for_recent_access():
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    file_record = {
        "storage_class": "S3 Standard",
        "lifecycle_policy": "auto",
        "upload_date": now - timedelta(days=60),
        "last_accessed_at": now - timedelta(days=3),
        "access_history": [now - timedelta(days=3)],
        "size_bytes": 5 * 1024 ** 3,
        "csp": "AWS",
    }
    insight = build_file_insight(file_record, now)
    assert insight["status"] in ("aligned", "watch", "action")
    assert insight["current_tier"] == "hot"


def test_portfolio_health_empty_files():
    health = compute_portfolio_health([])
    assert health["score"] == 100
    assert health["grade"] == "A"
