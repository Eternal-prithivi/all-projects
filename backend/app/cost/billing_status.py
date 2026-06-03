"""Per-user multi-cloud billing connectivity probes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from app.byoc.credential_resolver import get_byoc_status
from app.config.demo_mode import is_demo_mode
from app.cost.manager import get_aws_cost_and_usage, get_azure_billing_data, get_gcp_billing_data


def _probe_provider(
    username: str,
    provider: str,
    start_str: str,
    end_str: str,
) -> Dict[str, Any]:
    if provider == "aws":
        data = get_aws_cost_and_usage(username, start_str, end_str, "DAILY")
    elif provider == "gcp":
        data = get_gcp_billing_data(username, start_str, end_str)
    else:
        data = get_azure_billing_data(username, start_str, end_str)

    status = data.get("status")
    if status in ("missing_config", "missing_dependency", "error"):
        return {
            "provider": provider,
            "live": False,
            "status": status,
            "message": data.get("message") or data.get("error", "Unavailable"),
            "setup_steps": data.get("implementation_steps", []),
        }

    has_rows = bool(data.get("ResultsByTime") or data.get("Services"))
    return {
        "provider": provider,
        "live": has_rows or is_demo_mode(),
        "status": "demo" if is_demo_mode() else ("ok" if has_rows else "no_data"),
        "message": "Billing data available" if has_rows else "Connected but no rows in range",
        "currency": data.get("Currency", "USD"),
    }


def get_user_billing_status(username: str) -> Dict[str, Any]:
    """Summarize whether AWS/GCP/Azure billing works for this user."""
    end = datetime.utcnow()
    start = end - timedelta(days=14)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    byoc = get_byoc_status(username)
    providers = {}
    for key in ("aws", "gcp", "azure"):
        entry = _probe_provider(username, key, start_str, end_str)
        entry["byoc_connected"] = bool((byoc.get(key) or {}).get("connected"))
        providers[key] = entry

    live_count = sum(1 for p in providers.values() if p.get("live"))
    return {
        "username": username,
        "demo_mode": is_demo_mode(),
        "date_range": {"start": start_str, "end": end_str},
        "providers": providers,
        "summary": {
            "live_providers": live_count,
            "total_providers": 3,
            "ready_for_unified_dashboard": live_count >= 1,
        },
    }
