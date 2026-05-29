import pytest
from app.cost import manager


def test_get_gcp_billing_placeholder():
    result = manager.get_gcp_billing_data("testuser", "2023-01-01", "2023-01-02")
    assert isinstance(result, dict)
    assert "message" in result


def test_get_azure_billing_placeholder():
    result = manager.get_azure_billing_data("testuser", "2023-01-01", "2023-01-02")
    assert isinstance(result, dict)
    assert "message" in result


def test_get_aws_cost_and_usage_calls_ce_client(monkeypatch):
    class FakeClient:
        def get_cost_and_usage(self, **kwargs):
            return {"ResultsByTime": []}

    def fake_build_ce(username):
        assert username == "alice"
        return FakeClient(), False

    monkeypatch.setattr(
        "app.cost.manager.build_aws_ce_client", fake_build_ce
    )

    resp = manager.get_aws_cost_and_usage("alice", "2023-01-01", "2023-01-02")
    assert isinstance(resp, dict)
    assert "ResultsByTime" in resp
