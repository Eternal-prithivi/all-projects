"""
Meter storage-related cloud API operations per user for pass-through billing.

Rates are conservative USD estimates per operation (list/upload/download/sync).
Update STORAGE_OPERATION_RATES_USD when provider pricing changes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.mongo_client import get_database
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

COLLECTION = "storage_api_metering"

# USD per single API operation (published list/transaction tiers, rounded up slightly).
STORAGE_OPERATION_RATES_USD: Dict[str, Dict[str, float]] = {
    "AWS": {
        "list_buckets": 0.0,
        "get_bucket_location": 0.0,
        "list_objects": 0.0000004,
        "upload": 0.000005,
        "download": 0.0000004,
    },
    "GCP": {
        "list_buckets": 0.000005,
        "list_objects": 0.000005,
        "upload": 0.000005,
        "download": 0.0000004,
    },
    "Azure": {
        "list_containers": 0.000005,
        "list_objects": 0.000005,
        "upload": 0.000005,
        "download": 0.0000004,
    },
}

_CSP_ALIASES = {
    "AWS": "AWS",
    "GCP": "GCP",
    "GOOGLE": "GCP",
    "AZURE": "Azure",
    "MICROSOFT": "Azure",
}


def normalize_meter_csp(csp: str) -> Optional[str]:
    key = (csp or "").strip().upper()
    return _CSP_ALIASES.get(key)


OPERATION_LABELS: Dict[str, str] = {
    "list_buckets": "List buckets",
    "get_bucket_location": "Bucket region lookup",
    "list_containers": "List containers",
    "list_objects": "List / sync objects",
    "upload": "Upload",
    "download": "Download (presigned GET)",
}


def _period_key(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y-%m")


def _collection():
    return get_database()[COLLECTION]


def record_storage_meter_event(
    username: str,
    csp: str,
    operation: str,
    *,
    count: int = 1,
) -> None:
    """Increment metered usage for the current calendar month. Never raises."""
    if not username or count <= 0:
        return
    csp = normalize_meter_csp(csp)
    operation = (operation or "").strip()
    if not csp:
        return
    rates = STORAGE_OPERATION_RATES_USD.get(csp)
    if not rates or operation not in rates:
        return
    unit_usd = rates[operation] * count
    if unit_usd == 0.0 and count == 0:
        return
    period = _period_key()
    op_count_field = f"by_csp.{csp}.{operation}"
    try:
        _collection().update_one(
            {"username": username, "period": period},
            {
                "$inc": {
                    op_count_field: count,
                    f"estimated_usd.{csp}": unit_usd,
                    "estimated_usd.total": unit_usd,
                },
                "$set": {"updated_at": datetime.utcnow().isoformat()},
            },
            upsert=True,
        )
    except Exception as exc:
        logger.warning("storage_meter_event failed for %s: %s", username, exc)


def list_object_api_pages(object_count: int, page_size: int = 1000) -> int:
    """How many list-objects API calls a sync likely used."""
    if object_count <= 0:
        return 1
    return max(1, (object_count + page_size - 1) // page_size)


def get_storage_metering_summary(
    username: str,
    *,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate metered storage API costs for a user across YYYY-MM periods (inclusive).
    Defaults to the current month.
    """
    now = datetime.utcnow()
    start = start_period or _period_key(now)
    end = end_period or start

    query: Dict[str, Any] = {"username": username}
    if start == end:
        query["period"] = start
    else:
        query["period"] = {"$gte": start, "$lte": end}

    docs = list(_collection().find(query, {"_id": 0}))
    by_csp: Dict[str, Dict[str, int]] = {"AWS": {}, "GCP": {}, "Azure": {}}
    estimated_usd = {"AWS": 0.0, "GCP": 0.0, "Azure": 0.0, "total": 0.0}
    periods: List[str] = []

    for doc in docs:
        periods.append(doc.get("period", ""))
        for csp, ops in (doc.get("by_csp") or {}).items():
            if csp not in by_csp:
                by_csp[csp] = {}
            for op, n in (ops or {}).items():
                by_csp[csp][op] = by_csp[csp].get(op, 0) + int(n or 0)
        for csp, amount in (doc.get("estimated_usd") or {}).items():
            if csp == "total":
                estimated_usd["total"] += float(amount or 0)
            elif csp in estimated_usd:
                estimated_usd[csp] += float(amount or 0)

    operations_detail: List[Dict[str, Any]] = []
    for csp in ("AWS", "GCP", "Azure"):
        for op, n in sorted((by_csp.get(csp) or {}).items()):
            rate = STORAGE_OPERATION_RATES_USD.get(csp, {}).get(op, 0.0)
            operations_detail.append(
                {
                    "csp": csp,
                    "operation": op,
                    "label": OPERATION_LABELS.get(op, op),
                    "count": n,
                    "rate_usd": rate,
                    "estimated_usd": round(rate * n, 6),
                }
            )

    return {
        "username": username,
        "start_period": start,
        "end_period": end,
        "periods": sorted(set(periods)),
        "by_csp": by_csp,
        "estimated_usd": {
            "AWS": round(estimated_usd["AWS"], 6),
            "GCP": round(estimated_usd["GCP"], 6),
            "Azure": round(estimated_usd["Azure"], 6),
            "total": round(estimated_usd["total"], 6),
        },
        "operations": operations_detail,
        "rates_source": "Zenith published storage API rate table (pass-through estimate)",
    }


def get_platform_storage_metering_summary(
    *,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
) -> Dict[str, Any]:
    """Roll up metered storage API usage across all users (platform operator view)."""
    now = datetime.utcnow()
    start = start_period or _period_key(now)
    end = end_period or start

    query: Dict[str, Any] = {}
    if start == end:
        query["period"] = start
    else:
        query["period"] = {"$gte": start, "$lte": end}

    docs = list(_collection().find(query, {"_id": 0}))
    user_count = len({d.get("username") for d in docs if d.get("username")})
    by_csp: Dict[str, Dict[str, int]] = {"AWS": {}, "GCP": {}, "Azure": {}}
    estimated_usd = {"AWS": 0.0, "GCP": 0.0, "Azure": 0.0, "total": 0.0}

    for doc in docs:
        for csp, ops in (doc.get("by_csp") or {}).items():
            if csp not in by_csp:
                by_csp[csp] = {}
            for op, n in (ops or {}).items():
                by_csp[csp][op] = by_csp[csp].get(op, 0) + int(n or 0)
        for csp, amount in (doc.get("estimated_usd") or {}).items():
            if csp == "total":
                estimated_usd["total"] += float(amount or 0)
            elif csp in estimated_usd:
                estimated_usd[csp] += float(amount or 0)

    return {
        "start_period": start,
        "end_period": end,
        "active_users": user_count,
        "estimated_usd": {
            "AWS": round(estimated_usd["AWS"], 6),
            "GCP": round(estimated_usd["GCP"], 6),
            "Azure": round(estimated_usd["Azure"], 6),
            "total": round(estimated_usd["total"], 6),
        },
        "by_csp": by_csp,
    }
