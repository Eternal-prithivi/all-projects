"""GET /api/cloud/availability — per-user provider sets."""

import pytest

pytestmark = pytest.mark.integration


def test_cloud_availability_returns_features(client, auth_headers):
    headers, _user = auth_headers()
    response = client.get("/api/cloud/availability", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["credential_mode"] in ("byoc", "platform")
    assert "storage" in body["features"]
    assert "providers" in body["features"]["storage"]
    assert isinstance(body["features"]["storage"]["providers"], list)
