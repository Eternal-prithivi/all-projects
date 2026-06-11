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


def test_authenticated_user_creates_ticket(client, auth_headers):
    headers, user = auth_headers()
    with patch("app.support.routes_support.email_service.send_contact_notification"):
        response = client.post(
            "/api/support/tickets",
            headers=headers,
            json={
                "category": "billing",
                "subject": "billing",
                "body": "Question about my invoice",
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ticket"]["reference_code"].startswith("ZN-")
    assert body["messages"][0]["body"] == "Question about my invoice"

    listed = client.get("/api/support/tickets", headers=headers)
    assert listed.status_code == 200
    refs = [t["reference_code"] for t in listed.json()["tickets"]]
    assert body["ticket"]["reference_code"] in refs


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


def test_customer_message_notifies_admins_ws(client, auth_headers):
    _, admin = auth_headers(role="admin")
    user_headers, user = auth_headers()
    with patch("app.contact.routes_contact.email_service.send_contact_notification"), patch(
        "app.contact.routes_contact.email_service.send_auto_reply"
    ):
        submit = client.post(
            "/api/contact/submit",
            json={
                "name": user["username"],
                "email": user["email"],
                "subject": "support",
                "message": "Initial",
            },
            headers=user_headers,
        )
    ref = submit.json()["reference_code"]
    sent = []

    async def capture_ws(message, user_id):
        sent.append((user_id, message))

    with patch(
        "app.support.ws_notify.manager.send_personal_message",
        side_effect=capture_ws,
    ), patch("app.support.routes_support.email_service.send_admin_customer_reply_notification"):
        reply = client.post(
            f"/api/support/tickets/{ref}/messages",
            headers=user_headers,
            json={"body": "Follow-up from customer"},
        )
    assert reply.status_code == 200
    assert len(sent) >= 1
    admin_msgs = [m for u, m in sent if u == admin["username"]]
    assert admin_msgs
    import json

    payload = json.loads(admin_msgs[0])
    assert payload["event"] == "support_customer_reply"
    assert payload["reference_code"] == ref
    assert payload["ticket_id"]


def test_admin_reply_emits_support_reply_ws(client, auth_headers):
    user_headers, user = auth_headers()
    with patch("app.contact.routes_contact.email_service.send_contact_notification"), patch(
        "app.contact.routes_contact.email_service.send_auto_reply"
    ):
        submit = client.post(
            "/api/contact/submit",
            json={
                "name": user["username"],
                "email": user["email"],
                "subject": "support",
                "message": "Help",
            },
            headers=user_headers,
        )
    ticket_id = submit.json()["ticket_id"]
    ref = submit.json()["reference_code"]
    sent = []

    async def capture_ws(message, user_id):
        sent.append((user_id, message))

    admin_headers, _ = auth_headers(role="admin")
    with patch(
        "app.support.ws_notify.manager.send_personal_message",
        side_effect=capture_ws,
    ), patch("app.support.routes_admin_support.email_service.send_agent_reply_email"):
        reply = client.post(
            f"/api/admin/support/tickets/{ticket_id}/messages",
            headers=admin_headers,
            json={"body": "Agent reply here"},
        )
    assert reply.status_code == 200
    import json

    user_msgs = [m for u, m in sent if u == user["username"]]
    assert user_msgs
    payload = json.loads(user_msgs[0])
    assert payload["event"] == "support_reply"
    assert payload["reference_code"] == ref
    assert payload["ticket_id"]


def test_legacy_admin_submissions_requires_admin(client, auth_headers):
    user_headers, _ = auth_headers()
    denied = client.get("/api/contact/admin/submissions", headers=user_headers)
    assert denied.status_code == 403

    admin_headers, _ = auth_headers(role="admin")
    ok = client.get("/api/contact/admin/submissions", headers=admin_headers)
    assert ok.status_code == 200
