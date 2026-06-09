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


def test_profile_picture_upload_and_remove(client, auth_headers, db):
    headers, user = auth_headers()
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    upload = client.post(
        "/api/profile/picture",
        headers=headers,
        files={"file": ("avatar.png", tiny_png, "image/png")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["success"] is True
    assert body["profile_picture"].startswith("data:image/png;base64,")

    me = client.get("/api/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["profile_picture"].startswith("data:image/png;base64,")

    profile = client.get("/api/profile/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["profile_picture"].startswith("data:image/png;base64,")

    stored = db["users"].find_one({"username": user["username"]})
    assert stored["profile_picture"].startswith("data:image/png;base64,")

    remove = client.delete("/api/profile/picture", headers=headers)
    assert remove.status_code == 200

    me_after = client.get("/api/users/me", headers=headers)
    assert me_after.json()["profile_picture"] is None


def test_profile_stats_reflect_user_resources(client, auth_headers, db):
    headers, user = auth_headers()
    username = user["username"]

    db["vm_assignments"].insert_one({
        "user_id": username,
        "vm_name": "test-vm",
        "status": "active",
    })
    db["files"].insert_one({
        "owner_username": username,
        "filename": "stats-test.bin",
        "size_bytes": 1024 ** 3,
    })

    response = client.get("/api/profile/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_vms_created"] >= 1
    assert data["storage_used_tb"] > 0
    assert isinstance(data["total_spend"], (int, float))
    assert data["member_since"]


def test_delete_account_soft_deletes_and_blocks_login(client, auth_headers, db):
    headers, user = auth_headers()
    username = user["username"]
    password = user["password"]

    delete_response = client.delete("/api/profile/account", headers=headers)
    assert delete_response.status_code == 200

    stored = db["users"].find_one({"username": username})
    assert stored["deleted"] is True
    assert stored["status"] == "deleted"
    assert db["sessions"].count_documents({"username": username}) == 0

    login_response = client.post(
        "/api/auth/token",
        data={"username": username, "password": password},
    )
    assert login_response.status_code == 401


def test_profile_picture_rejects_invalid_type(client, auth_headers):
    headers, _user = auth_headers()
    response = client.post(
        "/api/profile/picture",
        headers=headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
