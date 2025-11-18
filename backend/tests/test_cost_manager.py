import pytest
from app.cost import manager


def test_get_gcp_billing_placeholder():
    result = manager.get_gcp_billing_data("2023-01-01", "2023-01-02")
    assert isinstance(result, dict)
    assert "message" in result


def test_get_azure_billing_placeholder():
    result = manager.get_azure_billing_data("2023-01-01", "2023-01-02")
    assert isinstance(result, dict)
    assert "message" in result


def test_get_aws_cost_and_usage_calls_boto3(monkeypatch):
    # Create a fake client with the expected method
    class FakeClient:
        def get_cost_and_usage(self, **kwargs):
            return {"ResultsByTime": []}

    def fake_boto3_client(service_name, **kwargs):
        assert service_name == 'ce'
        return FakeClient()

    monkeypatch.setattr(manager, 'boto3', type('b', (), {'client': fake_boto3_client}))

    resp = manager.get_aws_cost_and_usage("2023-01-01", "2023-01-02")
    assert isinstance(resp, dict)
    assert "ResultsByTime" in resp
