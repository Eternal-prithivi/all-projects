"""Tests for storage lifecycle policy resolution and user actions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.storage.lifecycle_policy import (
    demotion_thresholds,
    pending_is_due,
    suggest_lifecycle_policy,
)
from app.storage.lifecycle_service import apply_lifecycle_action
from app.storage.tiering_tasks import _meets_demotion_thresholds, _process_demotion_candidate


def test_suggest_lifecycle_policy_mappings():
    assert suggest_lifecycle_policy("performance", "frequent") == "keep_hot"
    assert suggest_lifecycle_policy("cost", "archival") == "aggressive"
    assert suggest_lifecycle_policy("balanced", "infrequent") == "auto"


def test_aggressive_demotion_thresholds_are_shorter():
    auto_hot, auto_cold = demotion_thresholds("auto")
    agg_hot, agg_cold = demotion_thresholds("aggressive")
    assert agg_hot < auto_hot
    assert agg_cold < auto_cold


def test_meets_demotion_thresholds_respects_policy():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    base = {
        "csp": "AWS",
        "storage_class": "S3 Standard",
        "size_bytes": 10 * 1024 * 1024 * 1024,
        "tier_transition_count": 0,
    }
    file_record = {
        **base,
        "lifecycle_policy": "auto",
        "upload_date": now - timedelta(days=35),
        "last_accessed_at": now - timedelta(days=35),
    }
    assert _meets_demotion_thresholds(file_record, "warm", now) is True
    file_record["lifecycle_policy"] = "aggressive"
    assert _meets_demotion_thresholds(file_record, "warm", now) is True
    file_record["upload_date"] = now - timedelta(days=20)
    file_record["last_accessed_at"] = now - timedelta(days=20)
    assert _meets_demotion_thresholds(file_record, "warm", now) is True
    file_record["lifecycle_policy"] = "auto"
    assert _meets_demotion_thresholds(file_record, "warm", now) is False


def test_pending_is_due():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    pending = {"execute_after": now - timedelta(hours=1)}
    assert pending_is_due(pending, now) is True
    pending_future = {"execute_after": now + timedelta(days=2)}
    assert pending_is_due(pending_future, now) is False


@patch("app.storage.lifecycle_service.notification_service.create_notification")
def test_apply_lifecycle_action_keep_hot(mock_notify):
    files_db = MagicMock()
    file_record = {
        "_id": "id1",
        "filename": "report.pdf",
        "owner_username": "alice",
        "lifecycle_pending_demotion": {"target_tier": "warm"},
    }
    files_db.find_one.return_value = file_record
    result = apply_lifecycle_action(files_db, "alice", "report.pdf", "keep_hot")
    assert result["action"] == "keep_hot"
    files_db.update_one.assert_called_once()
    update_args = files_db.update_one.call_args[0][1]
    assert update_args["$set"]["lifecycle_policy"] == "keep_hot"
    assert "lifecycle_pending_demotion" in update_args["$unset"]


@patch("app.storage.tiering_tasks.notify_pending_demotion")
def test_process_demotion_candidate_creates_pending(mock_notify):
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    files_db = MagicMock()
    file_record = {
        "_id": "id1",
        "filename": "old.zip",
        "owner_username": "alice",
        "lifecycle_policy": "auto",
        "csp": "AWS",
        "s3_key": "alice/old.zip",
        "storage_class": "S3 Standard",
    }
    candidate = {
        "file_record": file_record,
        "target_tier": "warm",
        "priority": {
            "factors": {"estimated_monthly_savings": 1.25},
        },
    }
    files_db.find_one.return_value = file_record
    with patch("app.storage.tiering_tasks.get_user_lifecycle_preferences", return_value={"lifecycle_notice_days": 7}):
        outcome = _process_demotion_candidate(files_db, candidate, {}, now)
    assert outcome == "pending"
    mock_notify.assert_called_once()
    files_db.update_one.assert_called()
