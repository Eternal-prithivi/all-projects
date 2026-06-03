"""Tests for VM adaptive agent."""

from app.vm.adaptive_agent import run_adaptive_control_cycle
from app.utils.config import settings


def test_adaptive_agent_skips_without_gcp(monkeypatch):
    monkeypatch.setattr(settings, "GCP_SERVICE_ACCOUNT_JSON_PATH", "")
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    result = run_adaptive_control_cycle()
    assert result.get("skipped") is True
