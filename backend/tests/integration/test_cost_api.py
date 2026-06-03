"""Cost API integration tests — billing connectivity."""

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
