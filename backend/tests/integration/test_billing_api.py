"""Billing API smoke integration tests."""

from unittest.mock import patch

import pytest

from app.billing.routes_billing import CostBreakdown

pytestmark = pytest.mark.integration


def test_billing_invoices_requires_auth(client):
    response = client.get("/api/billing/invoices")
    assert response.status_code == 401


@patch("app.billing.routes_billing.fetch_real_cloud_costs")
def test_billing_invoices_authenticated(mock_costs, client, auth_headers):
    mock_costs.return_value = CostBreakdown()
    headers, _user = auth_headers()
    response = client.get("/api/billing/invoices", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "invoices" in body
