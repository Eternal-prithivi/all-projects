"""Settings API integration tests."""

import pytest

pytestmark = pytest.mark.integration


def test_get_settings_defaults(client, auth_headers):
    headers, _user = auth_headers()
    response = client.get("/api/settings/", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "notifications" in body
    assert "preferences" in body
    assert body["preferences"]["currency"]


def test_update_preferences(client, auth_headers, db):
    headers, user = auth_headers()
    response = client.put(
        "/api/settings/preferences",
        headers=headers,
        json={
            "theme": "dark",
            "language": "en",
            "timezone": "UTC",
            "date_format": "MM/DD/YYYY",
            "currency": "USD",
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    stored = db["users"].find_one({"username": user["username"]})
    assert stored["settings"]["preferences"]["theme"] == "dark"


def test_update_platform_region_slug(client, auth_headers, db, monkeypatch):
    import json
    from app.cloud import platform_storage_catalog as catalog

    regions = [
        {
            "slug": "asia",
            "label": "Asia",
            "aws": {"bucket": "b1", "region": "ap-south-1"},
            "gcp": {"bucket": "g1", "location": "ASIA-SOUTH1"},
            "azure": {
                "account_name": "a1",
                "account_key": "k1",
                "container": "c1",
                "region": "centralindia",
            },
        },
        {
            "slug": "europe",
            "label": "Europe",
            "aws": {"bucket": "b2", "region": "eu-west-1"},
            "gcp": {"bucket": "g2", "location": "EUROPE-WEST1"},
            "azure": {
                "account_name": "a2",
                "account_key": "k2",
                "container": "c2",
                "region": "westeurope",
            },
        },
    ]
    monkeypatch.setattr(catalog.settings, "PLATFORM_STORAGE_CATALOG", json.dumps(regions))
    catalog.invalidate_platform_catalog_cache()

    headers, user = auth_headers()
    response = client.put(
        "/api/settings/preferences",
        headers=headers,
        json={
            "theme": "dark",
            "language": "en",
            "timezone": "UTC",
            "date_format": "MM/DD/YYYY",
            "currency": "USD",
            "platform_region_slug": "europe",
        },
    )
    assert response.status_code == 200

    stored = db["users"].find_one({"username": user["username"]})
    assert stored["settings"]["preferences"]["platform_region_slug"] == "europe"

    get_resp = client.get("/api/settings/", headers=headers)
    body = get_resp.json()
    assert body["platform_multi_region"] is True
    assert len(body["platform_regions"]) == 2


def test_update_preferences_invalid_theme(client, auth_headers):
    headers, _user = auth_headers()
    response = client.put(
        "/api/settings/preferences",
        headers=headers,
        json={
            "theme": "neon",
            "language": "en",
            "timezone": "UTC",
            "date_format": "MM/DD/YYYY",
            "currency": "USD",
        },
    )
    assert response.status_code == 400


def test_notification_channel_settings_round_trip(client, auth_headers):
    headers, _user = auth_headers()
    payload = {
        "email_notifications": True,
        "budget_alerts": {"email": True, "in_app": False},
        "security_alerts": {"email": False, "in_app": True},
        "weekly_reports": {"email": False, "in_app": True},
        "maintenance_updates": {"email": True, "in_app": True},
    }
    put = client.put("/api/settings/notifications", headers=headers, json=payload)
    assert put.status_code == 200

    get_resp = client.get("/api/settings/", headers=headers)
    notif = get_resp.json()["notifications"]
    assert notif["budget_alerts"]["email"] is True
    assert notif["budget_alerts"]["in_app"] is False


def test_named_api_key_create_and_list(client, auth_headers, db, monkeypatch):
    from app.payments import plan_entitlements

    monkeypatch.setattr(plan_entitlements, "require_feature", lambda *_a, **_k: None)

    headers, user = auth_headers()
    create = client.post(
        "/api/settings/api-keys",
        headers=headers,
        json={"name": "CI Pipeline"},
    )
    assert create.status_code == 200
    body = create.json()
    assert body["name"] == "CI Pipeline"
    assert body["key"].startswith("sk-prod-")

    listed = client.get("/api/settings/api-keys", headers=headers)
    assert listed.status_code == 200
    keys = listed.json()["keys"]
    assert any(k.get("name") == "CI Pipeline" for k in keys)

    stored = list(db["api_keys"].find({"username": user["username"]}))
    assert any(doc.get("name") == "CI Pipeline" for doc in stored)
