"""Unit tests: DEMO_MODE prevents real billing SDK usage paths."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def demo_settings(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.utils import config as config_mod
    from app.config import demo_mode as demo_mod

    config_mod.settings = config_mod.Settings()
    demo_mod.DEMO_MODE = config_mod.settings.DEMO_MODE
    yield config_mod.settings
    config_mod.settings = config_mod.Settings()
    demo_mod.DEMO_MODE = config_mod.settings.DEMO_MODE


def test_aws_cost_returns_mock_without_ce_client(demo_settings):
    from app.cost.manager import get_aws_cost_and_usage

    with patch("app.storage.cloud_credentials.build_aws_ce_client") as mock_ce:
        data = get_aws_cost_and_usage("user1", "2025-01-01", "2025-01-10", "DAILY")
        mock_ce.assert_not_called()

    assert "ResultsByTime" in data
    assert len(data["ResultsByTime"]) >= 1


def test_gcp_billing_returns_mock_without_bigquery(demo_settings):
    from app.cost.manager import get_gcp_billing_data

    data = get_gcp_billing_data("user1", "2025-01-01", "2025-01-10")
    assert data.get("TotalCost", 0) > 0
    assert "ResultsByTime" in data
