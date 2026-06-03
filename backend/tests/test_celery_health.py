"""Celery health probe tests."""

from app.ops.celery_health import (
    celery_health_snapshot,
    get_beat_schedule_summary,
)


def test_beat_schedule_lists_storage_optimization():
    summary = get_beat_schedule_summary()
    assert summary["task_count"] >= 1
    assert "run-storage-optimization-nightly" in summary.get("tasks", [])
    assert "update-rl-policy-daily" in summary.get("tasks", [])
    assert "federated-statistics-weekly" in summary.get("tasks", [])


def test_celery_health_snapshot_shape():
    snapshot = celery_health_snapshot()
    assert "broker" in snapshot
    assert "workers" in snapshot
    assert "beat_schedule" in snapshot
    assert "healthy" in snapshot
    assert snapshot["beat_schedule"]["task_count"] >= 1
