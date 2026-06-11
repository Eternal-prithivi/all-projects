"""Persist daily cost snapshots in Mongo — read on dashboard load (no cloud APIs)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.database.mongo_client import get_database
from app.config.demo_mode import billing_results_by_time, is_demo_mode

COLLECTION = "dashboard_cost_snapshots"


def _collection():
    return get_database()[COLLECTION]


def extract_daily_totals(cost_payload: Dict[str, Any]) -> Dict[str, float]:
    """Sum daily amounts from a provider billing payload."""
    daily: Dict[str, float] = {}
    for item in billing_results_by_time(cost_payload):
        period = item.get("TimePeriod") or {}
        date_key = (period.get("Start") or "")[:10]
        if not date_key:
            continue
        amount = float(
            item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0) or 0
        )
        daily[date_key] = round(daily.get(date_key, 0.0) + amount, 4)
    return daily


def save_daily_snapshots(username: str, daily_totals: Dict[str, float]) -> None:
    """Upsert per-day totals for a user (called only on explicit cost refresh)."""
    if not daily_totals:
        return
    now = datetime.utcnow()
    col = _collection()
    for date_key, total_usd in daily_totals.items():
        col.update_one(
            {"username": username, "date": date_key},
            {
                "$set": {
                    "username": username,
                    "date": date_key,
                    "total_usd": round(total_usd, 4),
                    "captured_at": now,
                    "demo_mode": is_demo_mode(),
                }
            },
            upsert=True,
        )


def get_cost_trend(username: str, *, days: int = 7) -> Dict[str, Any]:
    """Return last N days of stored snapshots — Mongo read only."""
    days = max(1, min(days, 30))
    end = datetime.utcnow().date()
    start = end - timedelta(days=days - 1)
    start_str = start.isoformat()
    end_str = end.isoformat()

    col = _collection()
    docs = list(
        col.find(
            {"username": username, "date": {"$gte": start_str, "$lte": end_str}},
            {"_id": 0, "date": 1, "total_usd": 1, "demo_mode": 1},
        ).sort("date", 1)
    )
    by_date = {d["date"]: float(d.get("total_usd", 0)) for d in docs}

    points: List[Dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        label = cursor.strftime("%a")
        points.append(
            {
                "date": key,
                "label": label,
                "value": round(by_date.get(key, 0.0), 2),
            }
        )
        cursor += timedelta(days=1)

    trend_pct = None
    trend_direction = None
    if len(points) >= 2:
        first_half = sum(p["value"] for p in points[: len(points) // 2])
        second_half = sum(p["value"] for p in points[len(points) // 2 :])
        if first_half > 0:
            change = ((second_half - first_half) / first_half) * 100
            trend_pct = round(abs(change), 1)
            trend_direction = "up" if change >= 0 else "down"
        elif second_half > 0:
            trend_pct = 100.0
            trend_direction = "up"

    has_data = any(p["value"] > 0 for p in points)
    demo = any(d.get("demo_mode") for d in docs) or is_demo_mode()

    return {
        "points": points,
        "trend_pct": trend_pct,
        "trend_direction": trend_direction,
        "has_data": has_data,
        "demo_mode": demo,
    }
