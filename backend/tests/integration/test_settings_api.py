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
