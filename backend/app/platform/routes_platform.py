"""Public platform status — no auth required."""

from datetime import datetime

from fastapi import APIRouter

from app.database.mongo_client import get_database, mongodb_client
from app.platform.cloud_connectivity import probe_platform_cloud_connectivity
from app.utils.config import settings as app_settings
from app.config.demo_mode import is_demo_mode

router = APIRouter(tags=["Platform"])


@router.get("/status")
async def get_platform_status():
    """
    Public snapshot for status page and maintenance gate.
    Does not expose secrets or PII.
    """
    maintenance_mode = False
    allow_new_registrations = True
    platform_name = "Zenith"

    try:
        db = get_database()
        platform_config = db["platform_settings"].find_one({"_id": "platform_config"})
        if platform_config:
            maintenance_mode = bool(platform_config.get("maintenance_mode", False))
            allow_new_registrations = bool(platform_config.get("allow_new_registrations", True))
            platform_name = platform_config.get("platform_name", platform_name)
    except Exception:
        pass

    mongo_ok = False
    try:
        mongo_ok = mongodb_client.is_connected() or mongodb_client.connect()
        if mongo_ok:
            get_database().command("ping")
            mongo_ok = True
    except Exception:
        mongo_ok = False

    cloud = probe_platform_cloud_connectivity()

    overall = "operational"
    if maintenance_mode:
        overall = "maintenance"
    elif not mongo_ok:
        overall = "degraded"

    return {
        "platform_name": platform_name,
        "overall": overall,
        "maintenance_mode": maintenance_mode,
        "allow_new_registrations": allow_new_registrations,
        "demo_mode": is_demo_mode(),
        "use_real_metrics": app_settings.USE_REAL_METRICS,
        "real_time_mode": app_settings.REAL_TIME_MODE,
        "services": {
            "api": "operational" if not maintenance_mode else "maintenance",
            "database": "operational" if mongo_ok else "degraded",
            "billing_data": "demo_mock" if is_demo_mode() else "live_apis",
        },
        "cloud_connectivity": cloud,
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
