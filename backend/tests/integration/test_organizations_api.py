"""Organizations API integration tests."""

import pytest

pytestmark = pytest.mark.integration


def test_create_org_invite_and_accept(client, auth_headers, user_factory):
    owner_headers, owner = auth_headers()
    member = user_factory(email="invitee@example.com")
    member_headers, _ = auth_headers(user=member)

    create = client.post(
        "/api/organizations",
        headers=owner_headers,
        json={"name": "Acme Corp"},
    )
    assert create.status_code == 200, create.text
    org_id = create.json()["org_id"]

    invite = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": "invitee@example.com", "role": "member"},
    )
    assert invite.status_code == 200
    token = invite.json()["invite_link"].split("/")[-1]

    preview = client.get(f"/api/organizations/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["org_name"] == "Acme Corp"

    accept = client.post(
        f"/api/organizations/invites/{token}/accept",
        headers=member_headers,
    )
    assert accept.status_code == 200
    assert accept.json()["org_id"] == org_id

    me = client.get("/api/organizations/me", headers=member_headers)
    assert me.status_code == 200
    assert me.json()["organization"]["name"] == "Acme Corp"


def test_owner_can_revoke_pending_invite(client, auth_headers):
    owner_headers, _ = auth_headers()

    client.post(
        "/api/organizations",
        headers=owner_headers,
        json={"name": "Revoke Test Org"},
    )

    invite = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": "pending@example.com", "role": "member"},
    )
    assert invite.status_code == 200

    revoke = client.delete(
        "/api/organizations/invites/pending@example.com",
        headers=owner_headers,
    )
    assert revoke.status_code == 200

    me = client.get("/api/organizations/me", headers=owner_headers)
    assert me.status_code == 200
    pending = me.json().get("pending_invites") or []
    assert not any(i.get("email") == "pending@example.com" for i in pending)


def test_invite_returns_email_sent_flag(client, auth_headers, monkeypatch):
    owner_headers, _ = auth_headers()
    client.post(
        "/api/organizations",
        headers=owner_headers,
        json={"name": "Email Flag Org"},
    )

    monkeypatch.setattr(
        "app.organizations.routes_organizations.email_service.send_org_invite",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        "app.organizations.routes_organizations.email_service.sender_email",
        "test@example.com",
    )

    invite = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": "newhire@example.com", "role": "member"},
    )
    assert invite.status_code == 200
    assert invite.json().get("email_sent") is True


def test_non_member_cannot_see_org_roster(client, auth_headers):
    owner_headers, _owner = auth_headers()
    outsider_headers, _outsider = auth_headers()

    client.post(
        "/api/organizations",
        headers=owner_headers,
        json={"name": "Private Team"},
    )

    outsider_view = client.get("/api/organizations/me", headers=outsider_headers)
    assert outsider_view.status_code == 200
    assert outsider_view.json()["organization"] is None
