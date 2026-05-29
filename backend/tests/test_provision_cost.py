"""Unit tests for provision cost_estimator (built-in table, no live Infracost)."""

from unittest.mock import patch

from app.provision.cost_estimator import (
    estimate_cost,
    estimate_from_config,
    estimate_with_infracost,
)


def test_static_site_free_tier_estimate():
    config = {"enable_s3": True, "bucket_name": "test-bucket"}
    result = estimate_from_config(config)
    assert result.available is True
    assert result.total_monthly_cost == "0.00"
    names = [r["name"] for r in result.resources]
    assert any("S3" in n for n in names)


def test_paid_ec2_instance_shows_cost():
    config = {"enable_ec2": True, "instance_type": "m5.large"}
    result = estimate_from_config(config)
    assert float(result.total_monthly_cost) > 0
    assert any("m5.large" in r.get("name", "") for r in result.resources)


def test_estimate_cost_falls_back_without_infracost():
    config = {"enable_vpc": True, "enable_ec2": True, "instance_type": "t2.micro"}
    with patch("app.provision.cost_estimator.check_infracost_installed", return_value=False):
        result = estimate_cost(config, workspace_dir="/tmp/fake")
    assert result.available is True
    assert result.total_monthly_cost == "0.00"


def test_estimate_with_infracost_missing_cli():
    result = estimate_with_infracost("/nonexistent/workspace")
    assert result.available is False
    assert result.error is not None
