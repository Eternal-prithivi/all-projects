"""Unit tests for platform cloud connectivity probes."""

from app.platform.cloud_connectivity import probe_platform_cloud_connectivity


def test_probe_returns_tri_cloud_shape():
    result = probe_platform_cloud_connectivity()
    assert "providers" in result
    assert set(result["providers"].keys()) == {"aws", "gcp", "azure"}
    for key in ("aws", "gcp", "azure"):
        provider = result["providers"][key]
        assert "storage" in provider
        assert provider["storage"] in ("configured", "not_configured", "not_supported")
    assert result["summary"]["total_providers"] == 3
