"""Profile API integration tests — sessions after login."""

import pytest

pytestmark = pytest.mark.integration


def test_profile_sessions_after_login(client, auth_headers, db):
    headers, user = auth_headers()
    response = client.get("/api/profile/sessions", headers=headers)
    assert response.status_code == 200
    sessions = response.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1
    assert any(s.get("current") for s in sessions)

    db_sessions = list(db["sessions"].find({"username": user["username"]}))
    assert len(db_sessions) >= 1


def test_profile_sessions_unauthorized(client):
    assert client.get("/api/profile/sessions").status_code == 401
