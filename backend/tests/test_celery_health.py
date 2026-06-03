"""Celery health probe tests."""

from app.ops.celery_health import get_beat_schedule_summary


def test_beat_schedule_lists_storage_optimization():
    summary = get_beat_schedule_summary()
    assert summary["task_count"] >= 1
    assert "run-storage-optimization-nightly" in summary.get("tasks", [])
