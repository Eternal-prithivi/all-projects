"""Admin API integration tests — RBAC, self-protection, audit export."""

from datetime import datetime

import pytest

pytestmark = pytest.mark.integration


def test_admin_dashboard_ok(client, auth_headers, db):
    headers, admin = auth_headers(role="admin")
    db["users"].insert_one(
        {
            "username": "other_user",
            "email": "other@example.com",
            "role": "user",
            "status": "active",
            "created_at": datetime.utcnow(),
        }
    )

    response = client.get("/api/admin/dashboard", headers=headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_users"] >= 2
    assert "monthly_revenue" in stats


def test_non_admin_forbidden(client, auth_headers):
    headers, _user = auth_headers(role="user")
    assert client.get("/api/admin/dashboard", headers=headers).status_code == 403
    assert client.get("/api/admin/users", headers=headers).status_code == 403


def test_admin_cannot_delete_self(client, auth_headers):
    headers, admin = auth_headers(role="admin")
    response = client.delete(
        f"/api/admin/users/{admin['username']}",
        headers=headers,
    )
    assert response.status_code == 400
    assert "own account" in response.json()["detail"].lower()


def test_admin_cannot_demote_self(client, auth_headers):
    headers, admin = auth_headers(role="admin")
    response = client.put(
        f"/api/admin/users/{admin['username']}/role",
        headers=headers,
        json={"role": "user"},
    )
    assert response.status_code == 400


def test_audit_export_csv(client, auth_headers, db):
    headers, admin = auth_headers(role="admin")
    db["admin_actions"].insert_one(
        {
            "admin_username": admin["username"],
            "action": "create_user",
            "target_user": "victim",
            "timestamp": datetime.utcnow(),
        }
    )

    response = client.get("/api/admin/audit-logs/export?format=csv", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert b"action" in response.content or b"create_user" in response.content


def test_admin_system_health_includes_celery(client, auth_headers):
    headers, _admin = auth_headers(role="admin")
    response = client.get("/api/admin/system-health", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    platform = body.get("platform") or {}
    celery = platform.get("celery") or {}
    assert "broker" in celery
    assert "beat_schedule" in celery


def test_production_admin_requires_2fa_enrollment(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.trust.account_gate.settings.ENVIRONMENT", "production")
    headers, _admin = auth_headers(role="admin", two_fa_enabled=False)
    response = client.get("/api/admin/dashboard", headers=headers)
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "ADMIN_2FA_REQUIRED"


def test_production_platform_owner_bypasses_2fa_enrollment(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.trust.account_gate.settings.ENVIRONMENT", "production")
    monkeypatch.setattr("app.trust.account_gate.settings.PLATFORM_OWNER_USERNAMES", "tanjiro")
    headers, admin = auth_headers(role="admin", username="tanjiro", two_fa_enabled=False)
    response = client.get("/api/admin/dashboard", headers=headers)
    assert response.status_code == 200, response.text


def test_production_default_owner_fallback(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.trust.account_gate.settings.ENVIRONMENT", "production")
    monkeypatch.setattr("app.trust.account_gate.settings.PLATFORM_OWNER_USERNAMES", "")
    headers, _admin = auth_headers(role="admin", username="tanjiro", two_fa_enabled=False)
    response = client.get("/api/admin/dashboard", headers=headers)
    assert response.status_code == 200, response.text
