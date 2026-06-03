from celery import shared_task
from datetime import datetime, timedelta
import numpy as np
import logging

from app.database.mongo_client import get_database
from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
from app.config.demo_mode import is_demo_mode
from app.cost.forecasting import extract_daily_costs

logger = logging.getLogger(__name__)
DB = get_database()
anomalies_collection = DB["cost_anomalies"]
byoc_collection = DB["byoc_credentials"]


def detect_anomaly_zscore(costs: list, threshold: float = 2.0) -> dict:
    """Detect anomalies using Z-score method"""
    if len(costs) < 7:
        return {"is_anomaly": False, "reason": "Insufficient data"}

    costs_array = np.array(costs)
    mean = np.mean(costs_array)
    std = np.std(costs_array)

    if std == 0:
        return {"is_anomaly": False, "reason": "No variation in costs"}

    latest_cost = costs[-1]
    z_score = (latest_cost - mean) / std

    is_anomaly = abs(z_score) > threshold

    return {
        "is_anomaly": is_anomaly,
        "z_score": float(z_score),
        "mean": float(mean),
        "std": float(std),
        "latest_cost": float(latest_cost),
        "deviation_percentage": float(((latest_cost - mean) / mean * 100) if mean > 0 else 0),
        "severity": "critical" if abs(z_score) > 3 else "warning" if abs(z_score) > 2 else "normal",
    }


def _fetch_provider_costs(username: str, provider: str, start_str: str, end_str: str) -> dict:
    if provider == "aws":
        return get_aws_cost_and_usage(username, start_str, end_str, "DAILY")
    if provider == "gcp":
        return get_gcp_billing_data(username, start_str, end_str)
    if provider == "azure":
        return get_azure_billing_data(username, start_str, end_str)
    return {}


def _usernames_with_byoc() -> list[str]:
    rows = byoc_collection.find({"is_active": True}, {"username": 1})
    return sorted({row["username"] for row in rows if row.get("username")})


def _scan_scope(username: str, provider: str, start_str: str, end_str: str) -> list[dict]:
    """Run anomaly detection for one username+provider; skip missing billing config."""
    cost_data = _fetch_provider_costs(username, provider, start_str, end_str)
    if cost_data.get("status") in {"missing_config", "missing_dependency", "error"}:
        return []

    costs = extract_daily_costs(cost_data)
    if len(costs) < 7:
        return []

    anomaly_result = detect_anomaly_zscore(costs)
    if not anomaly_result["is_anomaly"]:
        return []

    end_date = datetime.utcnow()
    return [
        {
            "provider": provider,
            "username": username,
            "scope": "byoc" if username != "platform" else "platform",
            "detected_at": datetime.utcnow(),
            "date": end_date.strftime("%Y-%m-%d"),
            "cost": anomaly_result["latest_cost"],
            "expected_cost": anomaly_result["mean"],
            "deviation_percentage": anomaly_result["deviation_percentage"],
            "severity": anomaly_result["severity"],
            "z_score": anomaly_result["z_score"],
            "acknowledged": False,
        }
    ]


@shared_task(name="check_cost_anomalies")
def check_cost_anomalies():
    """Daily Celery task — platform scan plus per-user BYOC where billing is configured."""
    if is_demo_mode():
        logger.info("⏭️  DEMO_MODE: skipping scheduled cost anomaly detection")
        return {"anomalies_found": 0, "skipped": True, "reason": "demo_mode"}

    logger.info("Starting cost anomaly detection...")

    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        providers = ["aws", "gcp", "azure"]
        anomalies_found = []

        for provider in providers:
            try:
                anomalies_found.extend(
                    _scan_scope("platform", provider, start_str, end_str)
                )
            except Exception as e:
                logger.error(f"Platform anomaly check failed for {provider}: {e}")

        for username in _usernames_with_byoc():
            for provider in providers:
                try:
                    anomalies_found.extend(
                        _scan_scope(username, provider, start_str, end_str)
                    )
                except Exception as e:
                    logger.error(
                        f"BYOC anomaly check failed for {username}/{provider}: {e}"
                    )

        for anomaly_doc in anomalies_found:
            anomalies_collection.insert_one(anomaly_doc)
            logger.warning(
                "Cost anomaly: user=%s provider=%s cost=$%.2f expected=$%.2f",
                anomaly_doc.get("username"),
                anomaly_doc.get("provider"),
                anomaly_doc.get("cost", 0),
                anomaly_doc.get("expected_cost", 0),
            )

        logger.info(f"Anomaly detection complete. Found {len(anomalies_found)} anomalies.")
        return {"anomalies_found": len(anomalies_found), "details": anomalies_found}

    except Exception as e:
        logger.error(f"Error in anomaly detection task: {str(e)}")
        return {"error": str(e)}
