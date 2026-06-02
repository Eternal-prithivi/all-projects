"""2FA API integration tests."""

import pyotp
import pytest

pytestmark = pytest.mark.integration


def test_disable_2fa_requires_code_when_enabled(client, auth_headers, db):
    secret = pyotp.random_base32()
    headers, user = auth_headers()
    db["users"].update_one(
        {"username": user["username"]},
        {
            "$set": {
                "two_fa_secret": secret,
                "two_fa_enabled": True,
                "two_fa_verified": True,
            }
        },
    )

    missing = client.post("/api/2fa/disable-2fa", headers=headers)
    assert missing.status_code == 400
    assert "code required" in missing.json()["detail"].lower()

    invalid = client.post(
        "/api/2fa/disable-2fa",
        headers=headers,
        json={"code": "000000"},
    )
    assert invalid.status_code == 400
    assert "invalid" in invalid.json()["detail"].lower()

    valid_code = pyotp.TOTP(secret).now()
    ok = client.post(
        "/api/2fa/disable-2fa",
        headers=headers,
        json={"code": valid_code},
    )
    assert ok.status_code == 200

    status = client.get("/api/2fa/status-2fa", headers=headers)
    assert status.json()["enabled"] is False


def test_disable_2fa_without_code_during_setup(client, auth_headers, db):
    secret = pyotp.random_base32()
    headers, user = auth_headers()
    db["users"].update_one(
        {"username": user["username"]},
        {
            "$set": {
                "two_fa_secret": secret,
                "two_fa_enabled": False,
                "two_fa_verified": False,
            }
        },
    )

    response = client.post("/api/2fa/disable-2fa", headers=headers)
    assert response.status_code == 200

    status = client.get("/api/2fa/status-2fa", headers=headers)
    assert status.json()["secret_exists"] is False
