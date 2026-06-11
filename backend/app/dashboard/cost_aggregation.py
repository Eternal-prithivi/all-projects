"""Aggregate dashboard costs across all providers available to the user (hybrid)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from app.cloud.availability import CloudFeature, available_providers
from app.cloud.providers import normalize_provider_key
from app.config.demo_mode import is_demo_mode, sum_billing_total

logger = logging.getLogger(__name__)

CACHE_TTL = 3600
_cost_cache: Dict[str, Dict[str, Any]] = {}


def _monthly_range() -> Tuple[str, str]:
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    return start_date, end_date


def _fetch_provider_billing(username: str, provider_key: str) -> Optional[Dict[str, Any]]:
    from app.cost.manager import (
        get_aws_cost_and_usage,
        get_azure_billing_data,
        get_gcp_billing_data,
    )

    start_date, end_date = _monthly_range()
    if provider_key == "aws":
        data = get_aws_cost_and_usage(username, start_date, end_date, "DAILY")
    elif provider_key == "gcp":
        data = get_gcp_billing_data(username, start_date, end_date)
    elif provider_key == "azure":
        data = get_azure_billing_data(username, start_date, end_date)
    else:
        return None

    if data.get("status") in ("missing_config", "missing_dependency", "error"):
        logger.info(
            "Dashboard cost skip %s for %s: %s",
            provider_key,
            username,
            data.get("message") or data.get("error"),
        )
        return None

    return data


def _fetch_provider_total(username: str, provider_key: str) -> Optional[float]:
    data = _fetch_provider_billing(username, provider_key)
    if data is None:
        return None
    return float(sum_billing_total(data))


def refresh_user_costs(username: str, *, force: bool = False) -> Dict[str, Any]:
    """
    Refresh cached monthly totals for every cost-available provider (hybrid).
    Returns { monthly_costs, cost_by_provider, providers_included, ... }.
    """
    now = time.time()
    cached = _cost_cache.get(username)
    if (
        not force
        and cached
        and (now - cached.get("timestamp", 0)) < CACHE_TTL
    ):
        return cached

    from app.dashboard.cost_snapshots import extract_daily_totals, save_daily_snapshots

    providers = available_providers(username, CloudFeature.COST)
    by_provider: Dict[str, float] = {}
    skipped: Dict[str, str] = {}
    merged_daily: Dict[str, float] = {}

    for display in providers:
        key = normalize_provider_key(display)
        try:
            billing = _fetch_provider_billing(username, key)
            if billing is None:
                continue
            amount = float(sum_billing_total(billing))
            by_provider[key] = round(amount, 2)
            for day, val in extract_daily_totals(billing).items():
                merged_daily[day] = round(merged_daily.get(day, 0.0) + val, 4)
        except Exception as exc:
            logger.warning("Dashboard cost fetch failed %s/%s: %s", username, key, exc)
            skipped[key] = str(exc)

    if merged_daily:
        try:
            save_daily_snapshots(username, merged_daily)
        except Exception as exc:
            logger.warning("Failed to save cost snapshots for %s: %s", username, exc)

    total = round(sum(by_provider.values()), 2)
    payload = {
        "monthly_costs": total,
        "cost_by_provider": by_provider,
        "providers_included": list(by_provider.keys()),
        "providers_skipped": skipped,
        "timestamp": now,
        "cached_at": datetime.utcnow().isoformat() + "Z",
        "demo_mode": is_demo_mode(),
    }
    _cost_cache[username] = payload
    return payload


def get_cached_user_costs(username: str) -> Dict[str, Any]:
    """Return cache or empty shell (does not call cloud APIs)."""
    cached = _cost_cache.get(username)
    if cached:
        return cached
    return {
        "monthly_costs": 0.0,
        "cost_by_provider": {},
        "providers_included": [],
        "providers_skipped": {},
        "timestamp": 0,
        "cached_at": None,
        "demo_mode": is_demo_mode(),
    }
