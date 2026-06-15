"""Platform spend ledger and global circuit breaker for shared cloud keys."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.utils.config import settings


def _ledger():
    return get_database()["platform_spend_ledger"]


def _settings_doc() -> dict:
    return get_database()["platform_settings"].find_one({"_id": "platform_config"}) or {}


def record_platform_spend_event(
    username: str,
    *,
    category: str,
    estimated_usd: float,
    csp: str = "AWS",
    metadata: Optional[dict] = None,
) -> None:
    if estimated_usd <= 0:
        return
    now = datetime.utcnow()
    month_key = now.strftime("%Y-%m")
    _ledger().insert_one(
        {
            "username": username,
            "category": category,
            "estimated_usd": round(float(estimated_usd), 6),
            "csp": csp,
            "month_key": month_key,
            "metadata": metadata or {},
            "created_at": now,
        }
    )


def platform_monthly_spend_usd(month_key: Optional[str] = None) -> float:
    key = month_key or datetime.utcnow().strftime("%Y-%m")
    rows = list(
        _ledger().aggregate(
            [
                {"$match": {"month_key": key}},
                {"$group": {"_id": None, "total": {"$sum": "$estimated_usd"}}},
            ]
        )
    )
    return float(rows[0]["total"]) if rows else 0.0


def platform_budget_exceeded() -> bool:
    monthly_cap = float(getattr(settings, "PLATFORM_MONTHLY_BUDGET_USD", 0) or 0)
    if monthly_cap <= 0:
        plat = _settings_doc()
        monthly_cap = float(plat.get("platform_monthly_budget_usd") or 0)
    if monthly_cap <= 0:
        return False
    return platform_monthly_spend_usd() >= monthly_cap


def assert_platform_budget_available(username: str) -> None:
    if username in _owner_usernames():
        return
    if platform_budget_exceeded():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "platform_budget_exceeded",
                "message": (
                    "Zenith platform cloud capacity is temporarily full. "
                    "Connect BYOC in Settings or try again later."
                ),
            },
        )


def _owner_usernames() -> set[str]:
    raw = getattr(settings, "PLATFORM_OWNER_USERNAMES", "") or ""
    return {u.strip() for u in raw.split(",") if u.strip()}


def get_platform_spend_summary() -> Dict[str, Any]:
    month = datetime.utcnow().strftime("%Y-%m")
    return {
        "month_key": month,
        "estimated_usd": round(platform_monthly_spend_usd(month), 4),
        "budget_exceeded": platform_budget_exceeded(),
    }
