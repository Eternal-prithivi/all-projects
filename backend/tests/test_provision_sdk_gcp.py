"""Unit tests for GCP SDK provision modules (mocked)."""

from unittest.mock import MagicMock, patch

from app.provision.sdk_modules import gcp_gcs, gcp_network
from app.provision.sdk_modules.context import SdkDeployContext


def test_plan_gcs_requires_bucket_name():
    result = gcp_gcs.plan_gcs({"bucket_name": ""}, {})
    assert result["error"]


@patch("app.provision.sdk_modules.gcp_network.gcp_compute_clients")
def test_plan_gcp_network_success(mock_clients):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock(), "proj")
    result = gcp_network.plan_gcp_network({"gcp_region": "us-central1"}, {})
    assert result["error"] is None
    assert result["lines"]


@patch("app.provision.sdk_modules.gcp_network.gcp_compute_clients")
def test_apply_gcp_network_creates_vpc(mock_clients):
    from google.api_core import exceptions as gcp_exc

    networks = MagicMock()
    subnetworks = MagicMock()
    mock_clients.return_value = (networks, subnetworks, MagicMock(), "proj")
    networks.get.side_effect = gcp_exc.NotFound("missing")
    networks.insert.return_value.result.return_value = None
    subnetworks.get.side_effect = gcp_exc.NotFound("missing")
    subnetworks.insert.return_value.result.return_value = None
    ctx = SdkDeployContext()
    result = gcp_network.apply_gcp_network({"gcp_region": "us-central1"}, {}, ctx)
    assert result["success"] is True
    assert ctx.gcp_network_name == "zenith-vpc"
