"""Integration tests for async support tickets."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def test_contact_submit_creates_ticket(client, db):
    with patch("app.contact.routes_contact.email_service.send_contact_notification"), patch(
        "app.contact.routes_contact.email_service.send_auto_reply"
    ):
        response = client.post(
            "/api/contact/submit",
            json={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "subject": "support",
                "message": "Need help with VMs",
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["reference_code"].startswith("ZN-")

    ticket = db["support_tickets"].find_one({"reference_code": body["reference_code"]})
    assert ticket is not None
    messages = list(db["support_messages"].find({"ticket_id": ticket["_id"]}))
    assert len(messages) == 1


def test_guest_otp_flow(client, db):
    with patch("app.contact.routes_contact.email_service.send_contact_notification"), patch(
        "app.contact.routes_contact.email_service.send_auto_reply"
    ):
        submit = client.post(
            "/api/contact/submit",
            json={
                "name": "Guest User",
                "email": "guest@example.com",
                "subject": "billing",
                "message": "Billing question",
            },
        )
    ref = submit.json()["reference_code"]
    sent_otp = []

    def capture_otp(email, ref_code, otp):
        sent_otp.append(otp)
        return True

    with patch(
        "app.support.routes_support.email_service.send_ticket_otp_email",
        side_effect=capture_otp,
    ):
        req = client.post(
            "/api/support/guest/request-otp",
            json={"reference_code": ref, "email": "guest@example.com"},
        )
    assert req.status_code == 200
    assert len(sent_otp) == 1

    verify = client.post(
        "/api/support/guest/verify-otp",
        json={
            "reference_code": ref,
            "email": "guest@example.com",
            "code": sent_otp[0],
        },
    )
    assert verify.status_code == 200, verify.text
    token = verify.json()["guest_token"]
    assert verify.json()["ticket"]["reference_code"] == ref

    thread = client.get(
        f"/api/support/guest/tickets/{ref}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert thread.status_code == 200
    assert len(thread.json()["messages"]) >= 1


def test_user_lists_own_tickets(client, auth_headers):
    headers, user = auth_headers()
    with patch("app.contact.routes_contact.email_service.send_contact_notification"), patch(
        "app.contact.routes_contact.email_service.send_auto_reply"
    ):
        client.post(
            "/api/contact/submit",
            json={
                "name": user["username"],
                "email": user["email"],
                "subject": "general",
                "message": "My ticket",
            },
            headers=headers,
        )

    listed = client.get("/api/support/tickets", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


def test_admin_reply_requires_admin(client, auth_headers):
    user_headers, _user = auth_headers()
    with patch("app.contact.routes_contact.email_service.send_contact_notification"), patch(
        "app.contact.routes_contact.email_service.send_auto_reply"
    ):
        submit = client.post(
            "/api/contact/submit",
            json={
                "name": "Test",
                "email": "other@example.com",
                "subject": "support",
                "message": "Help",
            },
        )
    ticket_id = submit.json()["ticket_id"]

    denied = client.get("/api/admin/support/tickets", headers=user_headers)
    assert denied.status_code == 403

    admin_headers, _admin = auth_headers(role="admin")
    ok = client.get("/api/admin/support/tickets", headers=admin_headers)
    assert ok.status_code == 200

    with patch("app.support.routes_admin_support.email_service.send_agent_reply_email"):
        reply = client.post(
            f"/api/admin/support/tickets/{ticket_id}/messages",
            headers=admin_headers,
            json={"body": "We are looking into this."},
        )
    assert reply.status_code == 200
    assert len(reply.json()["messages"]) >= 2


def test_legacy_admin_submissions_requires_admin(client, auth_headers):
    user_headers, _ = auth_headers()
    denied = client.get("/api/contact/admin/submissions", headers=user_headers)
    assert denied.status_code == 403

    admin_headers, _ = auth_headers(role="admin")
    ok = client.get("/api/contact/admin/submissions", headers=admin_headers)
    assert ok.status_code == 200
