"""Notifications API integration tests."""

import pytest

pytestmark = pytest.mark.integration


def test_create_list_and_mark_read(client, auth_headers, db):
    headers, user = auth_headers()

    create = client.post(
        "/api/notifications",
        headers=headers,
        json={
            "title": "Hello",
            "message": "Test notification",
            "type": "info",
        },
    )
    assert create.status_code == 200
    nid = create.json()["id"]

    listing = client.get("/api/notifications", headers=headers)
    assert listing.status_code == 200
    items = listing.json()["notifications"]
    assert any(n["id"] == nid for n in items)

    read = client.patch(f"/api/notifications/{nid}/read", headers=headers)
    assert read.status_code == 200


def test_user_cannot_read_another_users_notifications(client, auth_headers, db):
    headers_a, user_a = auth_headers()
    headers_b, _user_b = auth_headers()

    create = client.post(
        "/api/notifications",
        headers=headers_a,
        json={"title": "Private", "message": "Only for A", "type": "info"},
    )
    nid = create.json()["id"]

    listing_b = client.get("/api/notifications", headers=headers_b)
    ids_b = {n["id"] for n in listing_b.json()["notifications"]}
    assert nid not in ids_b
