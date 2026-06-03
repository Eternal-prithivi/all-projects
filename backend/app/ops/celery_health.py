"""Celery broker/worker health probes for readiness endpoints."""

from __future__ import annotations

from typing import Any, Dict

from app.utils.config import settings


def get_beat_schedule_summary() -> Dict[str, Any]:
    try:
        from app.celery_worker import celery_app

        schedule = celery_app.conf.beat_schedule or {}
        return {
            "task_count": len(schedule),
            "tasks": sorted(schedule.keys()),
            "timezone": str(celery_app.conf.timezone),
        }
    except Exception as exc:
        return {"task_count": 0, "tasks": [], "error": str(exc)[:200]}


def check_celery_broker() -> Dict[str, Any]:
    broker = getattr(settings, "CELERY_BROKER_URL", None) or ""
    if not broker:
        return {
            "configured": False,
            "reachable": False,
            "detail": "CELERY_BROKER_URL is not set",
        }

    try:
        from app.celery_worker import celery_app

        conn = celery_app.connection()
        conn.ensure_connection(max_retries=1, timeout=3)
        conn.release()
        return {
            "configured": True,
            "reachable": True,
            "detail": "Broker connection OK",
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "detail": str(exc)[:200],
        }


def check_celery_workers() -> Dict[str, Any]:
    try:
        from app.celery_worker import celery_app

        inspector = celery_app.control.inspect(timeout=2.0)
        ping = inspector.ping() if inspector else None
        if ping:
            return {"workers_online": len(ping), "reachable": True, "workers": list(ping.keys())}
        return {
            "workers_online": 0,
            "reachable": False,
            "detail": "No workers responded to ping (worker may be stopped)",
        }
    except Exception as exc:
        return {
            "workers_online": 0,
            "reachable": False,
            "detail": str(exc)[:200],
        }


def celery_health_snapshot() -> Dict[str, Any]:
    broker = check_celery_broker()
    workers = check_celery_workers()
    return {
        "broker": broker,
        "workers": workers,
        "beat_schedule": get_beat_schedule_summary(),
        "healthy": bool(broker.get("reachable")),
    }
