"""Per-user cloud availability (BYOC vs platform mode)."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.cloud.availability import (
    CloudFeature,
    assert_provider_available,
    available_providers,
    build_availability_payload,
    user_has_any_byoc,
)


@pytest.mark.parametrize(
    "byoc_connected,platform_ok,feature,expected",
    [
        (["AWS"], {"AWS": True, "GCP": True, "Azure": True}, CloudFeature.STORAGE, ["AWS"]),
        ([], {"AWS": True, "GCP": True, "Azure": False}, CloudFeature.STORAGE, ["AWS", "GCP"]),
        (["AWS", "GCP"], {"AWS": True, "GCP": False, "Azure": True}, CloudFeature.STORAGE, ["AWS", "GCP"]),
        ([], {"AWS": True, "GCP": True, "Azure": False}, CloudFeature.VM, ["AWS", "GCP"]),
    ],
)
def test_available_providers_byoc_vs_platform(byoc_connected, platform_ok, feature, expected):
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


def test_assert_provider_available_raises_403():
    with patch("app.cloud.availability.available_providers", return_value=["AWS"]):
        with pytest.raises(HTTPException) as exc:
            assert_provider_available("alice", "GCP", CloudFeature.STORAGE)
        assert exc.value.status_code == 403
        assert exc.value.detail["code"] == "provider_not_available"


def test_build_payload_shape():
    with patch("app.cloud.availability.user_has_any_byoc", return_value=False):
        with patch(
            "app.cloud.availability.available_providers",
            side_effect=lambda u, f: ["AWS", "GCP"] if f != CloudFeature.VM else ["GCP"],
        ):
            payload = build_availability_payload("bob")
    assert payload["credential_mode"] == "platform"
    assert "storage" in payload["features"]
    assert payload["features"]["storage"]["multi_provider"] is True
    assert "Azure" not in payload["features"]["vm"]["providers"]
