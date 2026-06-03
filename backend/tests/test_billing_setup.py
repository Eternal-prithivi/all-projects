"""Billing setup wizard and config resolution tests."""

from unittest.mock import patch

import pytest

from app.cost.billing_config import (
    azure_billing_configured,
    gcp_billing_configured,
    gcp_setup_status,
    missing_gcp_config_payload,
)
from app.cost.billing_status import get_user_billing_status


def test_missing_gcp_config_payload_shape():
    payload = missing_gcp_config_payload()
    assert payload["status"] == "missing_config"
    assert len(payload["implementation_steps"]) >= 3


@patch("app.cost.billing_config.resolve_gcp_billing_ids")
def test_gcp_billing_configured(mock_ids):
    mock_ids.return_value = {"dataset_id": "ds", "table_id": "tbl", "is_byoc": False}
    assert gcp_billing_configured("user") is True
    mock_ids.return_value = {"dataset_id": "", "table_id": "tbl", "is_byoc": False}
    assert gcp_billing_configured("user") is False


@patch("app.cost.billing_config.resolve_azure_billing_creds")
def test_azure_billing_configured(mock_creds):
    mock_creds.return_value = {
        "subscription_id": "sub",
        "tenant_id": "t",
        "client_id": "c",
        "client_secret": "s",
        "is_byoc": True,
    }
    assert azure_billing_configured("user") is True


@patch("app.cost.billing_status.get_gcp_billing_data")
@patch("app.cost.billing_status.get_aws_cost_and_usage")
@patch("app.cost.billing_status.get_azure_billing_data")
@patch("app.cost.billing_status.is_demo_mode", return_value=False)
def test_billing_status_missing_config_not_live(
    _demo, mock_azure, mock_aws, mock_gcp, monkeypatch
):
    mock_aws.return_value = {"ResultsByTime": [{"Total": {}}]}
    mock_gcp.return_value = missing_gcp_config_payload()
    mock_azure.return_value = {
        "status": "missing_config",
        "message": "Azure billing not configured",
        "implementation_steps": ["step"],
    }
    monkeypatch.setattr(
        "app.cost.billing_status.get_byoc_status",
        lambda _u: {"aws": {"connected": False}, "gcp": {"connected": False}, "azure": {"connected": False}},
    )
    result = get_user_billing_status("probe_user")
    assert result["providers"]["gcp"]["live"] is False
    assert result["providers"]["gcp"]["status"] == "missing_config"
    assert result["providers"]["aws"]["live"] is True


@patch("app.cost.billing_config.get_byoc_status")
@patch("app.cost.billing_config.resolve_gcp_billing_ids")
def test_gcp_setup_status(mock_ids, mock_byoc):
    mock_ids.return_value = {
        "dataset_id": "billing_export",
        "table_id": "gcp_billing_export_v1_abc",
        "is_byoc": True,
    }
    mock_byoc.return_value = {"gcp": {"connected": True}}
    status = gcp_setup_status("user1")
    assert status["configured"] is True
    assert status["can_update_via_api"] is True
