"""Multi-cloud storage target payloads."""

from unittest.mock import patch

from app.cloud.storage_targets import build_storage_targets_payload


@patch("app.cloud.storage_targets._gcp_targets")
@patch("app.cloud.storage_targets._aws_targets")
@patch("app.cloud.storage_targets.available_providers", return_value=["AWS", "GCP"])
def test_build_storage_targets_hybrid(mock_avail, mock_aws, mock_gcp):
    mock_aws.return_value = {
        "csp": "AWS",
        "credential_source": "byoc",
        "storage": {"bucket": "b1", "region": "us-east-1", "key_prefix": "u/"},
        "security": {"bucket": "s1", "region": "us-east-1", "key_prefix": "u/"},
    }
    mock_gcp.return_value = {
        "csp": "GCP",
        "credential_source": "platform",
        "storage": {"bucket": "g1", "region": "us-central1-a", "key_prefix": "u/"},
        "security": {"bucket": "g1", "region": "us-central1-a", "key_prefix": "secure/u/"},
    }
    payload = build_storage_targets_payload("alice")
    assert payload["mode"] == "hybrid"
    assert payload["providers"] == ["AWS", "GCP"]
    assert payload["targets"]["AWS"]["credential_source"] == "byoc"
    assert payload["targets"]["GCP"]["credential_source"] == "platform"
