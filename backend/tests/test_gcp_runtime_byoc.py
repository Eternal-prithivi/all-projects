"""GCP BYOC runtime — platform-key guard and zone from BYOC location."""

from unittest.mock import MagicMock, patch

from app.vm.gcp_runtime import (
    gcp_compute_ready,
    gcp_zone,
    reset_gcp_username,
    set_gcp_username,
)


def test_gcp_compute_ready_with_byoc_only_no_platform_key():
    token = set_gcp_username("alice")
    try:
        with patch("app.vm.gcp_runtime._platform_credentials", return_value=None):
            with patch(
                "app.vm.gcp_runtime._resolve_byoc_compute",
                return_value={
                    "credentials": MagicMock(),
                    "zone": "asia-south1-a",
                    "project_id": "byoc-project",
                    "is_byoc": True,
                },
            ):
                assert gcp_compute_ready() is True
    finally:
        reset_gcp_username(token)


def test_gcp_zone_from_byoc_primary_location():
    token = set_gcp_username("alice")
    try:
        with patch(
            "app.vm.gcp_runtime._resolve_byoc_compute",
            return_value={
                "credentials": MagicMock(),
                "zone": "asia-south1-a",
                "project_id": "byoc-project",
                "is_byoc": True,
            },
        ):
            assert gcp_zone() == "asia-south1-a"
    finally:
        reset_gcp_username(token)


def test_gcp_compute_ready_false_without_platform_or_byoc():
    token = set_gcp_username("nobody")
    try:
        with patch("app.vm.gcp_runtime._platform_credentials", return_value=None):
            with patch("app.vm.gcp_runtime._resolve_byoc_compute", return_value=None):
                assert gcp_compute_ready() is False
    finally:
        reset_gcp_username(token)
