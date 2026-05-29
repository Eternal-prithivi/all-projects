"""Public platform status — no auth required."""

from datetime import datetime

from fastapi import APIRouter

from app.database.mongo_client import get_database, mongodb_client

router = APIRouter(tags=["Platform"])

DB = get_database()


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
        settings = DB["platform_settings"].find_one({"_id": "platform_config"})
        if settings:
            maintenance_mode = bool(settings.get("maintenance_mode", False))
            allow_new_registrations = bool(settings.get("allow_new_registrations", True))
            platform_name = settings.get("platform_name", platform_name)
    except Exception:
        pass

    mongo_ok = False
    try:
        mongo_ok = mongodb_client.client is not None
        if mongo_ok:
            DB.command("ping")
            mongo_ok = True
    except Exception:
        mongo_ok = False

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
        "services": {
            "api": "operational" if not maintenance_mode else "maintenance",
            "database": "operational" if mongo_ok else "degraded",
        },
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
