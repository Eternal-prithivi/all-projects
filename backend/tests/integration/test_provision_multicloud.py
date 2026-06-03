"""Provision API multi-cloud integration tests."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_templates_gcp(client, auth_headers):
    headers, _ = auth_headers(two_fa_enabled=False)
    response = client.get("/api/provision/templates?csp=GCP", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["csp"] == "GCP"
    keys = {t["key"] for t in body["templates"]}
    assert "static-gcs" in keys


@patch("app.provision.routes_provision.resolve_provision_engine", return_value="terraform")
@patch("app.provision.routes_provision._resolve_provision_env")
@patch("app.provision.routes_provision.full_policy_check")
@patch("app.provision.routes_provision.estimate_cost")
def test_plan_gcp_requires_byoc(
    mock_cost,
    mock_policy,
    mock_env,
    mock_engine,
    client,
    auth_headers,
):
    mock_policy.return_value.model_dump.return_value = {"blocks": [], "warnings": [], "can_deploy": True}
    mock_cost.return_value.model_dump.return_value = {"available": True, "total_monthly_cost": "0"}
    mock_env.return_value = ({}, "Connect GCP under Settings")

    headers, _ = auth_headers(two_fa_enabled=False)
    response = client.post(
        "/api/provision/plan",
        headers=headers,
        json={
            "csp": "GCP",
            "template": "static-gcs",
            "enable_gcs": True,
            "bucket_name": "zenith-test-gcs-bucket",
            "gcp_region": "us-central1",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["stage"] == "credentials"
