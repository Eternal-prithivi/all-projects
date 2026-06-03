"""Platform diagnostics for admin and readiness probes."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from app.config.demo_mode import is_demo_mode
from app.database.mongo_client import mongodb_client, get_database
from app.ops.celery_health import celery_health_snapshot
from app.utils.config import settings
from app.utils.gcp_credentials import gcp_credentials_file_present


def platform_diagnostics_snapshot() -> Dict[str, Any]:
    """Full diagnostics snapshot — safe for admin (no secrets)."""
    mongo_ok = False
    try:
        mongo_ok = mongodb_client.is_connected() or mongodb_client.connect()
        if mongo_ok:
            get_database().command("ping")
    except Exception:
        mongo_ok = False

    db = get_database()
    byoc_active = {
        "AWS": db["byoc_credentials"].count_documents({"csp": "AWS", "is_active": True}),
        "GCP": db["byoc_credentials"].count_documents({"csp": "GCP", "is_active": True}),
        "Azure": db["byoc_credentials"].count_documents({"csp": "Azure", "is_active": True}),
    }

    return {
        "service": "zenith-api",
        "environment": getattr(settings, "ENVIRONMENT", "development"),
        "demo_mode": is_demo_mode(),
        "build": {
            "git_commit": os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GIT_COMMIT")
            or "unknown",
            "render_service": os.getenv("RENDER_SERVICE_NAME", ""),
        },
        "mongo_connected": mongo_ok,
        "gcp_credentials_present": gcp_credentials_file_present(),
        "celery_broker_configured": bool(getattr(settings, "CELERY_BROKER_URL", "")),
        "celery": celery_health_snapshot(),
        "byoc_active_connections": byoc_active,
        "feature_flags": {
            "vm_auto_migrate": bool(getattr(settings, "VM_AUTO_MIGRATE_ENABLED", False)),
            "use_real_metrics": bool(getattr(settings, "USE_REAL_METRICS", False)),
            "real_time_mode": bool(getattr(settings, "REAL_TIME_MODE", False)),
        },
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
