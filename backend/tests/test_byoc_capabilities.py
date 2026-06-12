"""Unit tests for BYOC per-feature capability engine."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.byoc.capabilities import (
    assert_byoc_feature_ready,
    build_byoc_capabilities_payload,
    byoc_features_ready,
    byoc_setup_gaps,
)
from app.cloud.availability import CloudFeature, build_availability_payload


def _byoc_status(connected: dict[str, bool]):
    return {
        "aws": {"connected": connected.get("aws", False)},
        "gcp": {"connected": connected.get("gcp", False)},
        "azure": {"connected": connected.get("azure", False)},
    }


def test_azure_storage_only_unlocks_storage_not_provision():
    azure_creds = {
        "is_byoc": True,
        "account_name": "acct",
        "account_key": "key",
    }

    with patch("app.byoc.capabilities.get_byoc_status", return_value=_byoc_status({"azure": True})):
        with patch("app.byoc.capabilities.resolve_azure_credentials", return_value=azure_creds):
            with patch("app.byoc.capabilities.azure_billing_configured", return_value=False):
                features = byoc_features_ready("alice", "Azure")

    assert features["storage"] is True
    assert features["security"] is True
    assert features["vm"] is False
    assert features["provision"] is False
    assert features["cost"] is False


def test_azure_full_sp_unlocks_compute_and_cost():
    azure_creds = {
        "is_byoc": True,
        "account_name": "acct",
        "account_key": "key",
        "subscription_id": "sub",
        "tenant_id": "tenant",
        "client_id": "client",
        "client_secret": "secret",
    }

    with patch("app.byoc.capabilities.get_byoc_status", return_value=_byoc_status({"azure": True})):
        with patch("app.byoc.capabilities.resolve_azure_credentials", return_value=azure_creds):
            with patch("app.byoc.capabilities.azure_billing_configured", return_value=True):
                features = byoc_features_ready("alice", "Azure")

    assert features["provision"] is True
    assert features["vm"] is True
    assert features["cost"] is True


def test_gcp_cost_requires_billing_ids():
    gcp_creds = {"is_byoc": True, "service_account_json": '{"type":"service_account"}'}

    with patch("app.byoc.capabilities.get_byoc_status", return_value=_byoc_status({"gcp": True})):
        with patch("app.byoc.capabilities.resolve_gcp_credentials", return_value=gcp_creds):
            with patch("app.byoc.capabilities.gcp_billing_configured", return_value=False):
                features = byoc_features_ready("alice", "GCP")
                gaps = byoc_setup_gaps("alice", "GCP")

    assert features["storage"] is True
    assert features["cost"] is False
    assert gaps[0]["code"] == "gcp_billing_export_missing"


def test_assert_byoc_feature_ready_raises_400_for_azure_sp_missing():
    azure_creds = {"is_byoc": True, "account_name": "a", "account_key": "k"}

    with patch("app.byoc.capabilities.get_byoc_status", return_value=_byoc_status({"azure": True})):
        with patch("app.byoc.capabilities.resolve_azure_credentials", return_value=azure_creds):
            with pytest.raises(HTTPException) as exc:
                assert_byoc_feature_ready("alice", "Azure", CloudFeature.PROVISION)

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "azure_sp_missing"


def test_availability_payload_includes_locked_providers():
    azure_creds = {"is_byoc": True, "account_name": "a", "account_key": "k"}

    def fake_byoc(username):
        return _byoc_status({"azure": True})

    with patch("app.cloud.availability.get_byoc_status", side_effect=fake_byoc):
        with patch("app.byoc.capabilities.get_byoc_status", side_effect=fake_byoc):
            with patch("app.byoc.capabilities.resolve_azure_credentials", return_value=azure_creds):
                with patch(
                    "app.cloud.availability._platform_configured",
                    side_effect=lambda p, f: p in ("AWS", "GCP"),
                ):
                    payload = build_availability_payload("bob")

    assert "Azure" not in payload["features"]["provision"]["providers"]
    locked = payload["features"]["provision"]["locked_providers"]
    assert any(x["csp"] == "Azure" for x in locked)
    assert payload["byoc_capabilities"]["azure"]["features"]["storage"] is True


def test_build_byoc_capabilities_payload_not_connected():
    with patch("app.byoc.capabilities.get_byoc_status", return_value=_byoc_status({})):
        payload = build_byoc_capabilities_payload("nobody")
    assert payload["aws"]["connected"] is False
    assert payload["aws"]["unlocked_features"] == []
