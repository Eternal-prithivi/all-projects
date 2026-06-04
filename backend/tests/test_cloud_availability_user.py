"""Per-user cloud availability (hybrid BYOC + platform)."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.cloud.availability import (
    CloudFeature,
    assert_provider_available,
    available_providers,
    build_availability_payload,
    platform_storage_configured,
    platform_vm_configured,
    resolve_credential_mode,
)


@pytest.mark.parametrize(
    "byoc_connected,platform_ok,feature,expected",
    [
        (
            ["AWS"],
            {"AWS": True, "GCP": True, "Azure": True},
            CloudFeature.STORAGE,
            ["AWS", "GCP", "Azure"],
        ),
        ([], {"AWS": True, "GCP": True, "Azure": False}, CloudFeature.STORAGE, ["AWS", "GCP"]),
        (
            ["AWS", "GCP"],
            {"AWS": True, "GCP": False, "Azure": True},
            CloudFeature.STORAGE,
            ["AWS", "GCP", "Azure"],
        ),
        ([], {"AWS": True, "GCP": True, "Azure": True}, CloudFeature.VM, ["AWS", "GCP", "Azure"]),
        ([], {"AWS": True, "GCP": True, "Azure": False}, CloudFeature.VM, ["AWS", "GCP"]),
    ],
)
def test_available_providers_hybrid_union(byoc_connected, platform_ok, feature, expected):
    def fake_byoc(username):
        return {
            "aws": {"connected": "AWS" in byoc_connected},
            "gcp": {"connected": "GCP" in byoc_connected},
            "azure": {"connected": "Azure" in byoc_connected},
        }

    def fake_platform(provider, feat):
        return platform_ok.get(provider, False)

    with patch("app.cloud.availability.get_byoc_status", side_effect=fake_byoc):
        with patch("app.cloud.availability._platform_configured", side_effect=fake_platform):
            assert available_providers("alice", feature) == expected


def test_hybrid_mode_label():
    def fake_byoc(username):
        return {"aws": {"connected": True}, "gcp": {"connected": False}, "azure": {"connected": False}}

    with patch("app.cloud.availability.get_byoc_status", side_effect=fake_byoc):
        with patch("app.cloud.availability._platform_configured", return_value=True):
            assert resolve_credential_mode("alice") == "hybrid"


def test_assert_provider_available_raises_403():
    with patch("app.cloud.availability.available_providers", return_value=["AWS"]):
        with pytest.raises(HTTPException) as exc:
            assert_provider_available("alice", "GCP", CloudFeature.STORAGE)
        assert exc.value.status_code == 403


def test_security_uses_hybrid_union_like_storage():
    """Security lists platform + BYOC clouds (same hybrid rules as storage)."""

    def fake_byoc(username):
        return {
            "aws": {"connected": True},
            "gcp": {"connected": False},
            "azure": {"connected": False},
        }

    def fake_platform(provider, feat):
        return provider in ("GCP", "Azure")

    with patch("app.cloud.availability.get_byoc_status", side_effect=fake_byoc):
        with patch("app.cloud.availability._platform_configured", side_effect=fake_platform):
            assert available_providers("alice", CloudFeature.SECURITY) == [
                "AWS",
                "GCP",
                "Azure",
            ]


def test_platform_gcp_listed_without_service_account_file():
    with patch("app.cloud.availability.gcp_credentials_file_present", return_value=False):
        assert platform_storage_configured("GCP") is True


def test_platform_gcp_vm_listed_without_service_account_file():
    with patch("app.cloud.availability.gcp_credentials_file_present", return_value=False):
        with patch("app.cloud.availability.settings.GCP_PROJECT_ID", "proj"), patch(
            "app.cloud.availability.settings.GCP_ZONE", "us-central1-a"
        ):
            assert platform_vm_configured("GCP") is True


def test_platform_azure_vm_listed_with_storage_and_sp_without_subscription():
    with patch("app.cloud.availability.settings.AZURE_SUBSCRIPTION_ID", ""), patch(
        "app.cloud.availability.settings.AZURE_TENANT_ID", "tenant"
    ), patch("app.cloud.availability.settings.AZURE_CLIENT_ID", "client"), patch(
        "app.cloud.availability.settings.AZURE_CLIENT_SECRET", "secret"
    ), patch(
        "app.cloud.availability.settings.AZURE_STORAGE_ACCOUNT_NAME", "acct"
    ), patch(
        "app.cloud.availability.settings.AZURE_STORAGE_ACCOUNT_KEY", "key"
    ), patch(
        "app.cloud.availability.settings.AZURE_CONTAINER_NAME", "container"
    ):
        assert platform_vm_configured("Azure") is True


def test_build_payload_hybrid():
    def fake_byoc(username):
        return {"aws": {"connected": True}, "gcp": {"connected": False}, "azure": {"connected": False}}

    with patch("app.cloud.availability.get_byoc_status", side_effect=fake_byoc):
        with patch(
            "app.cloud.availability._platform_configured",
            side_effect=lambda p, f: p in ("GCP", "Azure"),
        ):
            payload = build_availability_payload("bob")
    assert payload["credential_mode"] == "hybrid"
    assert "GCP" in payload["features"]["storage"]["providers"]
