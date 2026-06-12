"""Cost API integration tests — billing connectivity."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_billing_status_requires_auth(client):
    response = client.get("/api/cost/billing-status")
    assert response.status_code == 401


def test_billing_status_authenticated(client, auth_headers):
    headers, _user = auth_headers()
    response = client.get("/api/cost/billing-status", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body["providers"].keys()) == {"aws", "gcp", "azure"}
    for provider in body["providers"].values():
        assert "live" in provider
        assert "status" in provider


@patch("app.byoc.routes_byoc.ensure_gcp_buckets_exist", return_value=(True, "ready"))
@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_gcp_cost_blocked_without_billing_export(mock_test, _mock_buckets, client, auth_headers, pro_subscription, db):
    from tests.integration.test_byoc_api import _gcp_connect_payload, _gcp_ok_result

    mock_test.return_value = _gcp_ok_result()
    headers, user = auth_headers()
    pro_subscription(user["username"])
    client.post("/api/byoc/connect", headers=headers, json=_gcp_connect_payload())

    response = client.get(
        "/api/cost/gcp",
        headers=headers,
        params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "gcp_billing_export_missing"
