"""BYOC compute zone resolution from gcp_primary_location."""

from unittest.mock import patch

from app.vm.gcp_runtime import _byoc_compute_zone


def test_byoc_compute_zone_from_primary_location():
    with patch(
        "app.vm.gcp_runtime.get_user_cloud_credentials",
        return_value={"gcp_primary_location": "europe-west1"},
    ):
        assert _byoc_compute_zone("alice") == "europe-west1-b"
