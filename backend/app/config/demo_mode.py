# Demo Mode — mock billing/analytics reads (zero Cost Explorer / BigQuery / Consumption API cost).
# Set DEMO_MODE=true in backend/.env (and Render env). Does not block uploads or provision.

from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

from app.utils.config import settings

DEMO_MODE = settings.DEMO_MODE


def is_demo_mode() -> bool:
    return DEMO_MODE


def log_demo_mode_call(api_name: str) -> None:
    if DEMO_MODE:
        print(f"🎭 DEMO MODE: Using mock data for {api_name} (zero billing API cost)")


def _day_count(start_date: str, end_date: str) -> int:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return max(1, (end - start).days)


def _mock_results_by_time(
    start_date: str,
    end_date: str,
    *,
    daily_low: float = 8.0,
    daily_high: float = 45.0,
    service_names: List[str] | None = None,
) -> List[Dict[str, Any]]:
    service_names = service_names or ["Compute", "Storage", "Networking"]
    days = _day_count(start_date, end_date)
    results: List[Dict[str, Any]] = []
    start = datetime.strptime(start_date, "%Y-%m-%d")
    for i in range(days):
        date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        next_date = (start + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        daily_cost = round(random.uniform(daily_low, daily_high), 2)
        groups = []
        shares = [0.55, 0.30, 0.15]
        for name, share in zip(service_names, shares):
            groups.append({
                "Keys": [name],
                "Metrics": {
                    "UnblendedCost": {
                        "Amount": str(round(daily_cost * share, 2)),
                        "Unit": "USD",
                    }
                },
            })
        results.append({
            "TimePeriod": {"Start": date, "End": next_date},
            "Total": {"UnblendedCost": {"Amount": str(daily_cost), "Unit": "USD"}},
            "Groups": groups,
        })
    return results


class MockDataGenerator:
    @staticmethod
    def mock_aws_cost_data(
        start_date: str, end_date: str, granularity: str = "DAILY"
    ) -> Dict[str, Any]:
        if not DEMO_MODE:
            return None
        results = _mock_results_by_time(
            start_date,
            end_date,
            service_names=["Amazon EC2", "Amazon S3", "AWS CloudTrail"],
        )
        return {
            "ResultsByTime": results,
            "ResponseMetadata": {"RequestId": "mock-aws-ce"},
            "demo_mode": True,
        }

    @staticmethod
    def mock_gcp_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
        if not DEMO_MODE:
            return None
        results = _mock_results_by_time(
            start_date,
            end_date,
            daily_low=6.0,
            daily_high= 38.0,
            service_names=["Compute Engine", "Cloud Storage", "Cloud Monitoring"],
        )
        total = sum(float(r["Total"]["UnblendedCost"]["Amount"]) for r in results)
        services = [
            {"service": "Compute Engine", "cost": round(total * 0.55, 2), "currency": "USD"},
            {"service": "Cloud Storage", "cost": round(total * 0.30, 2), "currency": "USD"},
            {"service": "Cloud Monitoring", "cost": round(total * 0.15, 2), "currency": "USD"},
        ]
        return {
            "ResultsByTime": results,
            "Services": services,
            "TotalCost": round(total, 2),
            "Currency": "USD",
            "DimensionValueAttributes": [],
            "demo_mode": True,
        }

    @staticmethod
    def mock_azure_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
        if not DEMO_MODE:
            return None
        results = _mock_results_by_time(
            start_date,
            end_date,
            daily_low=5.0,
            daily_high= 32.0,
            service_names=["Virtual Machines", "Storage", "Bandwidth"],
        )
        total = sum(float(r["Total"]["UnblendedCost"]["Amount"]) for r in results)
        services = [
            {"service": "Virtual Machines", "cost": round(total * 0.50, 2), "currency": "USD"},
            {"service": "Storage", "cost": round(total * 0.35, 2), "currency": "USD"},
            {"service": "Bandwidth", "cost": round(total * 0.15, 2), "currency": "USD"},
        ]
        return {
            "ResultsByTime": results,
            "Services": services,
            "TotalCost": round(total, 2),
            "Currency": "USD",
            "DimensionValueAttributes": [],
            "demo_mode": True,
        }

    @staticmethod
    def mock_gcp_vm_metrics(vm_name: str) -> Dict[str, Any]:
        if not DEMO_MODE:
            return None
        return {
            "vm_name": vm_name,
            "cpu_usage": round(random.uniform(20, 80), 1),
            "memory_usage": round(random.uniform(30, 70), 1),
            "disk_io_mb": round(random.uniform(50, 200), 1),
            "network_io_mb": round(random.uniform(20, 100), 1),
            "active_users": random.randint(0, 3),
            "uptime_hours": round(random.uniform(1, 24), 1),
            "estimated_cost_usd": round(random.uniform(0.01, 0.50), 4),
            "status": "RUNNING",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def mock_budget_status(budget_amount: float) -> float:
        if not DEMO_MODE:
            return None
        return round(budget_amount * random.uniform(0.6, 0.9), 2)

    @staticmethod
    def mock_forecast_historical_days(days: int = 90) -> List[float]:
        """Synthetic daily costs for forecast when DEMO_MODE is on."""
        if not DEMO_MODE:
            return None
        base_cost = 10.0
        daily_increase = 0.15
        noise_level = 2.0
        historical: List[float] = []
        for day in range(days):
            cost = base_cost + (daily_increase * day) + random.uniform(-noise_level, noise_level)
            historical.append(max(0.01, cost))
        return historical


def billing_results_by_time(cost_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize AWS / GCP / Azure billing payloads to a ResultsByTime list."""
    if not cost_payload:
        return []
    if "ResultsByTime" in cost_payload:
        return cost_payload.get("ResultsByTime") or []
    nested = cost_payload.get("data")
    if isinstance(nested, dict) and "ResultsByTime" in nested:
        return nested.get("ResultsByTime") or []
    return []


def sum_billing_total(cost_payload: Dict[str, Any]) -> float:
    return sum(
        float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
        for item in billing_results_by_time(cost_payload)
    )
