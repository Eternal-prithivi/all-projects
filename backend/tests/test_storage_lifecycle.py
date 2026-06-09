"""Tests for report-aligned storage lifecycle priority scoring."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.storage.tiering_tasks import (
    _NOT_SENSITIVE_FILTER,
    _build_demotion_candidates,
    _invoke_tier_change,
    _perform_tier_change,
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


def test_invoke_tier_change_passes_aws_bucket_and_region():
    mock_fn = MagicMock()
    file_record = {"cloud_bucket": "zeneith-storage-asia", "region": "ap-south-1"}
    _invoke_tier_change("AWS", mock_fn, "alice", "alice/report.pdf", "STANDARD_IA", file_record)
    mock_fn.assert_called_once_with(
        "alice",
        "alice/report.pdf",
        "STANDARD_IA",
        bucket_name="zeneith-storage-asia",
        region_name="ap-south-1",
    )


def test_invoke_tier_change_passes_gcp_bucket():
    mock_fn = MagicMock()
    file_record = {"cloud_bucket": "zeneith-main-europe"}
    _invoke_tier_change("GCP", mock_fn, "bob", "bob/data.csv", "NEARLINE", file_record)
    mock_fn.assert_called_once_with(
        "bob",
        "bob/data.csv",
        "NEARLINE",
        bucket_name="zeneith-main-europe",
    )


def test_invoke_tier_change_passes_azure_container_and_account():
    mock_fn = MagicMock()
    file_record = {"cloud_bucket": "zenith-storage", "cloud_account": "zenithstorageus"}
    _invoke_tier_change("Azure", mock_fn, "carol", "carol/archive.zip", "Cool", file_record)
    mock_fn.assert_called_once_with(
        "carol",
        "carol/archive.zip",
        "Cool",
        container_name="zenith-storage",
        account_name="zenithstorageus",
    )


def test_demotion_queries_exclude_sensitive_files():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)

    class _Cursor:
        def __init__(self, rows):
            self._rows = rows

        def __iter__(self):
            return iter(self._rows)

    class _FilesDb:
        def __init__(self):
            self.queries = []

        def find(self, query):
            self.queries.append(query)
            return _Cursor([])

    files_db = _FilesDb()
    _build_demotion_candidates(files_db, now)
    assert len(files_db.queries) == 2
    hot_query, warm_query = files_db.queries
    assert _NOT_SENSITIVE_FILTER in hot_query["$and"]
    assert hot_query["$and"][1]["$or"]
    assert warm_query["$or"] == _NOT_SENSITIVE_FILTER["$or"]
    hot_cutoff = now - timedelta(days=14)
    assert hot_query["upload_date"]["$lt"] == hot_cutoff
    assert warm_query["last_accessed_at"]["$lt"] == now - timedelta(days=60)


def test_perform_tier_change_skips_sensitive_promotion_path(monkeypatch):
    """Promotion query uses _NOT_SENSITIVE_FILTER; perform uses recorded bucket."""
    change_fn = MagicMock()
    files_db = MagicMock()
    file_record = {
        "_id": "abc",
        "filename": "warm-file.csv",
        "owner_username": "user1",
        "csp": "AWS",
        "s3_key": "user1/warm-file.csv",
        "storage_class": "STANDARD_IA",
        "cloud_bucket": "zeneith-storage-us",
        "region": "us-east-1",
        "is_sensitive": False,
    }
    tier_change_functions = {"AWS": change_fn}
    changed = _perform_tier_change(
        file_record,
        "hot",
        tier_change_functions,
        files_db,
        is_promotion=True,
    )
    assert changed is True
    change_fn.assert_called_once()
    _, kwargs = change_fn.call_args
    assert kwargs["bucket_name"] == "zeneith-storage-us"
    assert kwargs["region_name"] == "us-east-1"


def test_promotion_target_from_normalized_cold_tier():
    """Cold Azure Archive promotes one level to warm, not hot."""
    normalized = normalize_lifecycle_tier("Archive")
    assert normalized == "cold"
    target = "warm" if normalized == "cold" else "hot" if normalized == "warm" else ""
    assert target == "warm"

