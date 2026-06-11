"""Unit tests for tri-cloud provision comparison."""

from unittest.mock import patch

from app.provision.cloud_compare import compare_clouds_for_intent
from app.provision.cost_estimator import estimate_from_config


def test_gcp_gce_cost_not_always_zero_for_paid_size():
    cfg = {
        "csp": "GCP",
        "template": "backend-app",
        "enable_gcp_network": True,
        "enable_gce": True,
        "machine_type": "e2-small",
        "disk_size_gb": 30,
    }
    est = estimate_from_config(cfg)
    assert float(est.total_monthly_cost) > 0


def test_compare_clouds_returns_sorted():
    with patch(
        "app.provision.cloud_compare.available_providers",
        return_value=["AWS", "GCP", "Azure"],
    ):
        rows = compare_clouds_for_intent(
            "testuser",
            template="backend-app",
            size_profile="micro",
            fit_base=75,
        )
    assert len(rows) == 3
    assert rows[0].get("badge") in ("best_fit", "best_value", None)
    assert "monthly_cost" in rows[0]
    assert "fit_score" in rows[0]
