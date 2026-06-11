"""Dashboard cost trend API — Mongo read only on GET."""

from datetime import datetime, timedelta

import pytest

from app.dashboard.cost_snapshots import get_cost_trend, save_daily_snapshots

pytestmark = pytest.mark.integration


def test_cost_trend_returns_points_without_cloud_call(client, auth_headers):
    headers, user = auth_headers()
    today = datetime.utcnow().date()
    yesterday = (today - timedelta(days=1)).isoformat()
    save_daily_snapshots(user["username"], {yesterday: 12.5})

    response = client.get("/api/dashboard/cost-trend?days=7", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "points" in body
    assert len(body["points"]) == 7
    assert body["has_data"] is True


def test_get_cost_trend_empty_when_no_snapshots():
    trend = get_cost_trend("no-such-user", days=7)
    assert trend["has_data"] is False
    assert len(trend["points"]) == 7
