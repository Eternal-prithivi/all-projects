"""Smoke integration tests for public platform endpoints."""

import pytest


pytestmark = pytest.mark.integration


def test_platform_status_returns_200(client):
    response = client.get("/api/platform/status")
    assert response.status_code == 200
    body = response.json()
    assert "overall" in body
    assert "services" in body
    assert body["platform_name"]


def test_platform_status_reflects_maintenance_flag(client, db):
    db["platform_settings"].update_one(
        {"_id": "platform_config"},
        {"$set": {"maintenance_mode": True}},
        upsert=True,
    )
    response = client.get("/api/platform/status")
    assert response.status_code == 200
    body = response.json()
    assert body["maintenance_mode"] is True
    assert body["overall"] == "maintenance"
