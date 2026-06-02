import pytest
from app.cost import manager


def test_get_gcp_billing_returns_demo_shape():
    """conftest sets DEMO_MODE=true; billing helpers return mock Cost Explorer-like data."""
    result = manager.get_gcp_billing_data("testuser", "2023-01-01", "2023-01-02")
    assert isinstance(result, dict)
    assert "ResultsByTime" in result
    assert result.get("Currency") == "USD"


def test_get_azure_billing_returns_demo_shape():
    result = manager.get_azure_billing_data("testuser", "2023-01-01", "2023-01-02")
    assert isinstance(result, dict)
    assert "ResultsByTime" in result
    assert result.get("Currency") == "USD"


def test_get_gcp_billing_missing_config_when_not_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    from app.utils import config as config_mod
    from app.config import demo_mode as demo_mod

    config_mod.settings = config_mod.Settings()
    demo_mod.DEMO_MODE = False

    result = manager.get_gcp_billing_data("testuser", "2023-01-01", "2023-01-02")
    assert result.get("status") == "missing_config"
    assert "message" in result


def test_get_aws_cost_and_usage_calls_ce_client(monkeypatch):
    class FakeClient:
        def get_cost_and_usage(self, **kwargs):
            return {"ResultsByTime": []}

    def fake_build_ce(username):
        assert username == "alice"
        return FakeClient(), False

    monkeypatch.setattr(
        "app.storage.cloud_credentials.build_aws_ce_client", fake_build_ce
    )

    resp = manager.get_aws_cost_and_usage("alice", "2023-01-01", "2023-01-02")
    assert isinstance(resp, dict)
    assert "ResultsByTime" in resp
