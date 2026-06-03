"""Billing connectivity tests."""

from app.cost.billing_status import get_user_billing_status
from app.config.demo_mode import is_demo_mode


def test_billing_status_returns_three_providers(monkeypatch):
    if not is_demo_mode():
        monkeypatch.setattr(
            "app.cost.billing_status.is_demo_mode",
            lambda: True,
        )
    result = get_user_billing_status("test_user_billing")
    assert "providers" in result
    assert set(result["providers"].keys()) == {"aws", "gcp", "azure"}
