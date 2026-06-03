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
    cloud = body.get("cloud_connectivity") or {}
    assert "providers" in cloud
    assert set(cloud["providers"].keys()) == {"aws", "gcp", "azure"}


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


def test_health_ready_includes_celery(client):
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "celery" in body
    assert "beat_schedule" in body["celery"]
