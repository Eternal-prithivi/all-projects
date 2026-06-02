"""Provision governance API — policy overrides and audit log (integration)."""

import pytest

from app.provision.audit_logger import log_provision_action

pytestmark = pytest.mark.integration


def test_builtin_policy_override_disable_and_reset(client, auth_headers, db):
    headers, user = auth_headers()
    builtin_name = "expensive_ec2_instance"

    disable = client.put(
        f"/api/provision/policy-rules/builtin/{builtin_name}",
        headers=headers,
        json={"enabled": False},
    )
    assert disable.status_code == 200
    assert disable.json()["enabled"] is False

    listing = client.get("/api/provision/policy-rules", headers=headers)
    assert listing.status_code == 200
    rules = listing.json()["rules"]
    rule = next(r for r in rules if r["name"] == builtin_name)
    assert rule["source"] == "override"
    assert rule["enabled"] is False
    assert rule["can_reset"] is True

    reset = client.delete(
        f"/api/provision/policy-rules/builtin/{builtin_name}",
        headers=headers,
    )
    assert reset.status_code == 200

    listing_after = client.get("/api/provision/policy-rules", headers=headers)
    rule_after = next(
        r for r in listing_after.json()["rules"] if r["name"] == builtin_name
    )
    assert rule_after["source"] == "builtin"
    assert rule_after.get("is_customized") is False

    # Cleanup overrides collection for this user
    db["provision_policy_overrides"].delete_many({"username": user["username"]})


def test_builtin_policy_unknown_returns_400(client, auth_headers):
    headers, _user = auth_headers()
    response = client.put(
        "/api/provision/policy-rules/builtin/not_a_real_rule",
        headers=headers,
        json={"enabled": False},
    )
    assert response.status_code == 400


def test_audit_log_pagination_and_export_csv(client, auth_headers, db):
    headers, user = auth_headers()
    username = user["username"]

    coll = db["provision_audit_log"]
    coll.delete_many({"actor": username})

    log_provision_action(
        action="plan",
        actor=username,
        deployment_id="integ-dep-1",
        status="success",
    )
    log_provision_action(
        action="policy_update",
        actor=username,
        deployment_id="governance",
        status="success",
        details={"builtin_name": "expensive_ec2_instance"},
    )

    page = client.get(
        "/api/provision/audit-log",
        headers=headers,
        params={"limit": 10, "skip": 0, "period_days": 90, "action": "all"},
    )
    assert page.status_code == 200
    body = page.json()
    assert body["total"] >= 2
    assert body["limit"] == 10
    assert "retention_days" in body

    policy_page = client.get(
        "/api/provision/audit-log",
        headers=headers,
        params={"limit": 10, "action": "policy", "period_days": 30},
    )
    assert policy_page.status_code == 200
    assert policy_page.json()["total"] >= 1
    assert all(
        e["action"].startswith("policy_") for e in policy_page.json()["events"]
    )

    export = client.get(
        "/api/provision/audit-log/export",
        headers=headers,
        params={"period_days": 90, "action": "all"},
    )
    assert export.status_code == 200
    assert "text/csv" in export.headers.get("content-type", "")
    assert "timestamp,action,status" in export.text
    assert "plan" in export.text

    coll.delete_many({"actor": username})


def test_audit_log_requires_auth(client):
    assert client.get("/api/provision/audit-log").status_code == 401
    assert client.get("/api/provision/audit-log/export").status_code == 401


def test_notifications_paginated_and_recent(client, auth_headers, db):
    headers, user = auth_headers()

    for i in range(3):
        client.post(
            "/api/notifications",
            headers=headers,
            json={
                "title": f"N{i}",
                "message": f"Message {i}",
                "type": "info",
            },
        )

    paginated = client.get(
        "/api/notifications",
        headers=headers,
        params={"limit": 5, "skip": 0, "read": "all", "type": "all"},
    )
    assert paginated.status_code == 200
    data = paginated.json()
    assert data["total"] == 3
    assert len(data["notifications"]) == 3
    assert data["has_more"] is False
    assert data["unread_count"] == 3
    assert "unread_count" in data

    recent = client.get(
        "/api/notifications/recent",
        headers=headers,
        params={"limit": 8},
    )
    assert recent.status_code == 200
    assert len(recent.json()["notifications"]) <= 8

    db["user_notifications"].delete_many({"username": user["username"]})
