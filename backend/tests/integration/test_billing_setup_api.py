"""Billing setup API integration tests."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_get_gcp_setup_status(client, auth_headers):
    headers, _user = auth_headers()
    response = client.get("/api/cost/setup/gcp", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "gcp"
    assert "setup_steps" in body
    assert "configured" in body


@patch("app.cost.routes_billing_setup.save_gcp_billing_setup")
def test_put_gcp_setup(mock_save, client, auth_headers):
    mock_save.return_value = {
        "success": True,
        "configured": True,
        "provider": "gcp",
    }
    headers, _user = auth_headers()
    response = client.put(
        "/api/cost/setup/gcp",
        headers=headers,
        json={
            "billing_dataset_id": "billing_ds",
            "billing_table_id": "gcp_billing_export_v1_test",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
