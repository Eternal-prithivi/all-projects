"""Tests for report-aligned storage lifecycle priority scoring."""

from datetime import datetime, timedelta, timezone

from app.storage.tiering_tasks import (
    calculate_lifecycle_priority,
    normalize_lifecycle_tier,
)


def test_normalize_lifecycle_tier_across_clouds():
    assert normalize_lifecycle_tier("S3 Standard") == "hot"
    assert normalize_lifecycle_tier("NEARLINE") == "warm"
    assert normalize_lifecycle_tier("Archive") == "cold"
    assert normalize_lifecycle_tier("unknown") is None


def test_lifecycle_priority_prefers_old_inactive_large_archives():
    now = datetime(2026, 5, 24, tzinfo=timezone.utc)
    archive = {
        "filename": "backup_2025-01-01.zip",
        "storage_class": "S3 Standard",
        "upload_date": now - timedelta(days=180),
        "last_accessed_at": now - timedelta(days=160),
        "access_frequency_score": 0,
        "size_mb": 50 * 1024,
    }
    active_doc = {
        "filename": "active-plan.docx",
        "storage_class": "S3 Standard",
        "upload_date": now - timedelta(days=35),
        "last_accessed_at": now - timedelta(days=31),
        "access_frequency_score": 8,
        "size_mb": 10,
    }

    archive_priority = calculate_lifecycle_priority(archive, "warm", now)
    active_priority = calculate_lifecycle_priority(active_doc, "warm", now)

    assert archive_priority["score"] > active_priority["score"]
    assert archive_priority["factors"]["file_type"] == "archive"
    assert archive_priority["factors"]["estimated_monthly_savings"] > 0
    assert archive_priority["current_tier"] == "hot"
    assert archive_priority["target_tier"] == "warm"

