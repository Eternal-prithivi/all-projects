"""Password reset and email verification API integration tests."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.auth.password_reset_service import _hash_value

pytestmark = pytest.mark.integration


@patch("app.auth.password_reset_service.EmailService")
def test_forgot_password_generic_response(mock_email_cls, client, user_factory):
    mock_email_cls.return_value.send_password_reset.return_value = True
    user = user_factory()

    response = client.post(
        "/api/auth/forgot-password",
        json={"identifier": user["email"], "method": "email"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_reset_password_invalid_token(client):
    response = client.post(
        "/api/auth/reset-password",
        json={
            "new_password": "NewPassword123!",
            "method": "email",
            "token": "not-a-real-token",
        },
    )
    assert response.status_code == 400


@patch("app.auth.password_reset_service.EmailService")
def test_reset_password_valid_token(mock_email_cls, client, user_factory, db):
    mock_email_cls.return_value.send_password_reset.return_value = True
    user = user_factory()
    token = "valid-reset-token-for-test"
    db["password_reset_requests"].insert_one(
        {
            "username": user["username"],
            "method": "email",
            "token_hash": _hash_value(token),
            "used": False,
            "expires_at": datetime.utcnow() + timedelta(hours=1),
        }
    )

    response = client.post(
        "/api/auth/reset-password",
        json={
            "new_password": "BrandNewPass1!",
            "method": "email",
            "token": token,
        },
    )
    assert response.status_code == 200

    login = client.post(
        "/api/auth/token",
        data={"username": user["username"], "password": "BrandNewPass1!"},
    )
    assert login.status_code == 200


def test_verify_email_with_valid_token(client, user_factory, db):
    token = "email-verify-token-abc"
    user = user_factory(email_verified=False)
    db["users"].update_one(
        {"username": user["username"]},
        {"$set": {"email_verify_token": token}},
    )
    db["platform_settings"].update_one(
        {"_id": "platform_config"},
        {"$set": {"require_email_verification": True}},
        upsert=True,
    )

    response = client.post(f"/api/auth/verify-email?token={token}")
    assert response.status_code == 200
