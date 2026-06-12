"""Team cloud health, roles, settings, and privacy filtering."""

from datetime import datetime

import pytest

pytestmark = pytest.mark.integration


def _create_org(client, headers, name="Health Org"):
    from app.database.mongo_client import get_database
    from bson import ObjectId

    res = client.post("/api/organizations", headers=headers, json={"name": name})
    assert res.status_code == 200
    org_id = res.json()["org_id"]
    get_database()["organizations"].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"seat_count": 10}},
    )
    return org_id


def test_patch_member_role_owner_only(client, auth_headers, user_factory):
    owner_headers, _ = auth_headers()
    admin_user = user_factory(email="roleadmin@example.com")
    admin_headers, _ = auth_headers(user=admin_user)
    _create_org(client, owner_headers)

    invite = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": admin_user["email"], "role": "admin"},
    )
    token = invite.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{token}/accept", headers=admin_headers)

    member = user_factory(email="rolemember@example.com")
    member_headers, member_user = auth_headers(user=member)
    inv2 = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    tok2 = inv2.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{tok2}/accept", headers=member_headers)

    denied = client.patch(
        f"/api/organizations/members/{member_user['username']}/role",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert denied.status_code == 403

    ok = client.patch(
        f"/api/organizations/members/{member_user['username']}/role",
        headers=owner_headers,
        json={"role": "admin"},
    )
    assert ok.status_code == 200
    assert ok.json()["role"] == "admin"


def test_transfer_ownership(client, auth_headers, user_factory):
    owner_headers, owner = auth_headers()
    _create_org(client, owner_headers, "Transfer Org")

    other = user_factory(email="newowner@example.com")
    other_headers, other_user = auth_headers(user=other)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": other["email"], "role": "admin"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{token}/accept", headers=other_headers)

    transfer = client.post(
        "/api/organizations/transfer-ownership",
        headers=owner_headers,
        json={"new_owner_username": other_user["username"]},
    )
    assert transfer.status_code == 200

    me = client.get("/api/organizations/me", headers=owner_headers)
    assert me.json()["my_role"] == "admin"
    me2 = client.get("/api/organizations/me", headers=other_headers)
    assert me2.json()["my_role"] == "owner"


def test_summary_admin_sees_member_spend(client, auth_headers, user_factory, monkeypatch):
    from app.database.mongo_client import get_database

    owner_headers, owner = auth_headers()
    org_id = _create_org(client, owner_headers, "Spend Org")

    member = user_factory(email="spender@example.com")
    member_headers, member_user = auth_headers(user=member)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{token}/accept", headers=member_headers)

    db = get_database()
    month = datetime.utcnow().strftime("%Y-%m")
    db["dashboard_cost_snapshots"].insert_one(
        {
            "username": member_user["username"],
            "date": f"{month}-01",
            "total_usd": 42.5,
            "captured_at": datetime.utcnow(),
        }
    )
    db["dashboard_cost_snapshots"].insert_one(
        {
            "username": owner["username"],
            "date": f"{month}-01",
            "total_usd": 10.0,
            "captured_at": datetime.utcnow(),
        }
    )

    from app.organizations import service

    service.invalidate_org_cache(org_id)

    admin_summary = client.get("/api/organizations/summary", headers=owner_headers)
    assert admin_summary.status_code == 200
    body = admin_summary.json()
    assert body["can_view_member_spend"] is True
    spends = {m["username"]: m["monthly_spend_usd"] for m in body["members"]}
    assert spends[member_user["username"]] == 42.5

    member_summary = client.get("/api/organizations/summary", headers=member_headers)
    assert member_summary.status_code == 200
    mbody = member_summary.json()
    assert mbody["can_view_member_spend"] is False
    assert mbody["org_totals"]["monthly_spend_usd"] >= 42.5
    own = [m for m in mbody["members"] if m["username"] == member_user["username"]][0]
    assert own.get("monthly_spend_usd") == 42.5
    other_rows = [m for m in mbody["members"] if m["username"] != member_user["username"]]
    for row in other_rows:
        assert "monthly_spend_usd" not in row


def test_org_settings_and_recommendations(client, auth_headers):
    owner_headers, _ = auth_headers()
    _create_org(client, owner_headers, "Settings Org")

    settings = client.patch(
        "/api/organizations/settings",
        headers=owner_headers,
        json={"monthly_budget_usd": 500, "approval_threshold_usd": 75},
    )
    assert settings.status_code == 200
    assert settings.json()["monthly_budget_usd"] == 500

    recs = client.get("/api/organizations/recommendations", headers=owner_headers)
    assert recs.status_code == 200
    assert "items" in recs.json()
