"""Auth API integration tests — register, login, JWT guards."""

import uuid

import pytest

pytestmark = pytest.mark.integration


def test_register_login_and_me(client, db):
    username = f"reg_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "SecurePass1!"

    reg = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["success"] is True

    token_resp = client.post(
        "/api/auth/token",
        data={"username": username, "password": password},
    )
    assert token_resp.status_code == 200
    token = token_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    me = client.get("/api/users/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == username
    assert body["email"] == email
    assert body["role"] == "user"


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_non_admin_cannot_access_admin_dashboard(client, auth_headers):
    headers, _user = auth_headers(role="user")
    response = client.get("/api/admin/dashboard", headers=headers)
    assert response.status_code == 403


def test_login_blocked_when_email_unverified(client, user_factory, db):
    user = user_factory(email_verified=False)
    db["platform_settings"].update_one(
        {"_id": "platform_config"},
        {"$set": {"require_email_verification": True}},
        upsert=True,
    )

    response = client.post(
        "/api/auth/token",
        data={"username": user["username"], "password": user["password"]},
    )
    assert response.status_code == 403
    assert "verify" in response.json()["detail"].lower()


def test_register_rejects_disposable_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "disposable_user",
            "email": "user@mailinator.com",
            "password": "SecurePass1!",
        },
    )
    assert response.status_code == 400
    assert "Disposable" in response.json()["detail"]


def test_register_requires_verification_before_login(client, db):
    import uuid

    username = f"verify_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "SecurePass1!"

    db["platform_settings"].update_one(
        {"_id": "platform_config"},
        {"$set": {"require_email_verification": True}},
        upsert=True,
    )

    reg = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["data"]["email_verification_required"] is True

    login_before = client.post(
        "/api/auth/token",
        data={"username": username, "password": password},
    )
    assert login_before.status_code == 403

    user = db["users"].find_one({"username": username})
    token = user["email_verify_token"]
    verify = client.post(f"/api/auth/verify-email?token={token}")
    assert verify.status_code == 200

    login_after = client.post(
        "/api/auth/token",
        data={"username": username, "password": password},
    )
    assert login_after.status_code == 200
