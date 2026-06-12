"""Phase 24 — org billing and resource ACL."""

import pytest

pytestmark = pytest.mark.integration


def test_member_inherits_org_plan_in_my_subscription(client, auth_headers, user_factory):
    owner_headers, owner = auth_headers()
    from app.database.mongo_client import get_database
    from bson import ObjectId

    create = client.post("/api/organizations", headers=owner_headers, json={"name": "Billing Org"})
    org_id = create.json()["org_id"]
    get_database()["organizations"].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"plan_id": "pro", "seat_count": 5, "subscription_status": "active"}},
    )

    member = user_factory(email="billmember@example.com")
    member_headers, _ = auth_headers(user=member)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    accept = client.post(f"/api/organizations/invites/{token}/accept", headers=member_headers)
    assert accept.status_code == 200, accept.text

    sub = client.get("/api/payments/my-subscription", headers=member_headers)
    assert sub.status_code == 200
    body = sub.json()
    assert body["plan_id"] == "pro"
    assert body.get("managed_by_org") is True or body["plan_name"]


def test_personal_checkout_blocked_for_org_member(client, auth_headers, user_factory):
    owner_headers, _ = auth_headers()
    from app.database.mongo_client import get_database
    from bson import ObjectId

    create = client.post("/api/organizations", headers=owner_headers, json={"name": "Block Org"})
    get_database()["organizations"].update_one(
        {"_id": ObjectId(create.json()["org_id"])},
        {"$set": {"seat_count": 5}},
    )

    member = user_factory(email="blockcheckout@example.com")
    member_headers, _ = auth_headers(user=member)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{token}/accept", headers=member_headers)

    order = client.post(
        "/api/payments/create-order",
        headers=member_headers,
        json={"plan_id": "basic", "billing_cycle": "monthly", "cloud_costs_usd": 0},
    )
    assert order.status_code == 400


def test_org_billing_summary(client, auth_headers):
    owner_headers, _ = auth_headers()
    client.post("/api/organizations", headers=owner_headers, json={"name": "Summary Org"})

    billing = client.get("/api/organizations/billing", headers=owner_headers)
    assert billing.status_code == 200
    data = billing.json()
    assert data["seat_count"] >= 1
    assert data["can_manage_billing"] is True


def test_seat_guard_on_accept(client, auth_headers, user_factory):
    owner_headers, _ = auth_headers()
    client.post("/api/organizations", headers=owner_headers, json={"name": "Seat Guard"})

    from app.database.mongo_client import get_database
    from bson import ObjectId

    me = client.get("/api/organizations/me", headers=owner_headers).json()
    org_id = me["organization"]["id"]
    get_database()["organizations"].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"seat_count": 1, "plan_id": "free"}},
    )

    member = user_factory(email="seatfull@example.com")
    member_headers, _ = auth_headers(user=member)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    accept = client.post(f"/api/organizations/invites/{token}/accept", headers=member_headers)
    assert accept.status_code == 402


def test_org_resources_summary(client, auth_headers):
    owner_headers, _ = auth_headers()
    client.post("/api/organizations", headers=owner_headers, json={"name": "Resources Org"})

    summary = client.get("/api/organizations/resources/summary", headers=owner_headers)
    assert summary.status_code == 200
    data = summary.json()
    assert "total_vms" in data
    assert "total_storage_gb" in data
    assert data.get("org_name") == "Resources Org"


def test_migrate_personal_subscription_to_org(client, auth_headers):
    owner_headers, owner = auth_headers()
    client.post("/api/organizations", headers=owner_headers, json={"name": "Migrate Org"})

    from app.database.mongo_client import get_database
    from datetime import datetime, timedelta

    db = get_database()
    db["subscriptions"].update_one(
        {"user_id": owner["username"]},
        {
            "$set": {
                "plan_id": "basic",
                "status": "active",
                "billing_cycle": "monthly",
                "current_period_start": datetime.utcnow(),
                "current_period_end": datetime.utcnow() + timedelta(days=30),
            }
        },
        upsert=True,
    )

    migrate = client.post("/api/organizations/billing/migrate-personal", headers=owner_headers)
    assert migrate.status_code == 200

    billing = client.get("/api/organizations/billing", headers=owner_headers)
    assert billing.json()["plan_id"] == "basic"

    sub = db["subscriptions"].find_one({"user_id": owner["username"]})
    assert sub.get("status") == "migrated_to_org"


def test_admin_lists_all_org_vms_member_lists_own(client, auth_headers, user_factory):
    from app.database.mongo_client import get_database
    from bson import ObjectId
    from datetime import datetime

    owner_headers, owner = auth_headers()
    create = client.post("/api/organizations", headers=owner_headers, json={"name": "ACL Org"})
    org_id = create.json()["org_id"]
    get_database()["organizations"].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"seat_count": 10}},
    )

    member = user_factory(email="aclmember@example.com")
    member_headers, _ = auth_headers(user=member)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{token}/accept", headers=member_headers)

    db = get_database()
    now = datetime.utcnow()
    db["vm_assignments"].insert_many(
        [
            {
                "assignment_id": "assign_owner_test",
                "user_id": owner["username"],
                "org_id": org_id,
                "created_by": owner["username"],
                "vm_name": "vm-owner",
                "status": "active",
                "assigned_at": now,
            },
            {
                "assignment_id": "assign_member_test",
                "user_id": member["username"],
                "org_id": org_id,
                "created_by": member["username"],
                "vm_name": "vm-member",
                "status": "active",
                "assigned_at": now,
            },
        ]
    )

    admin_list = client.get("/api/vm/my-assignments", headers=owner_headers)
    assert admin_list.status_code == 200
    admin_ids = {a["assignment_id"] for a in admin_list.json()}
    assert "assign_owner_test" in admin_ids
    assert "assign_member_test" in admin_ids

    member_list = client.get("/api/vm/my-assignments", headers=member_headers)
    member_ids = {a["assignment_id"] for a in member_list.json()}
    assert "assign_member_test" in member_ids
    assert "assign_owner_test" not in member_ids


def test_member_cannot_release_other_vm(client, auth_headers, user_factory):
    from app.database.mongo_client import get_database
    from bson import ObjectId
    from datetime import datetime

    owner_headers, owner = auth_headers()
    create = client.post("/api/organizations", headers=owner_headers, json={"name": "Release ACL"})
    org_id = create.json()["org_id"]
    get_database()["organizations"].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"seat_count": 10}},
    )

    member = user_factory(email="releaseacl@example.com")
    member_headers, _ = auth_headers(user=member)
    inv = client.post(
        "/api/organizations/invites",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    token = inv.json()["invite_link"].split("/")[-1]
    client.post(f"/api/organizations/invites/{token}/accept", headers=member_headers)

    get_database()["vm_assignments"].insert_one(
        {
            "assignment_id": "assign_other",
            "user_id": owner["username"],
            "org_id": org_id,
            "created_by": owner["username"],
            "vm_name": "vm-other",
            "status": "active",
            "assigned_at": datetime.utcnow(),
        }
    )

    denied = client.post("/api/vm/release/assign_other", headers=member_headers)
    assert denied.status_code == 404


def test_org_vm_quota_blocks_assignment(client, auth_headers):
    from app.database.mongo_client import get_database
    from bson import ObjectId
    from app.organizations.limits import assert_org_vm_quota
    from fastapi import HTTPException

    owner_headers, owner = auth_headers()
    create = client.post("/api/organizations", headers=owner_headers, json={"name": "Quota Org"})
    org_id = create.json()["org_id"]
    get_database()["organizations"].update_one(
        {"_id": ObjectId(org_id)},
        {"$set": {"plan_id": "free", "seat_count": 5}},
    )

    db = get_database()
    for i in range(2):
        db["vm_assignments"].insert_one(
            {
                "assignment_id": f"assign_quota_{i}",
                "user_id": owner["username"],
                "org_id": org_id,
                "created_by": owner["username"],
                "vm_name": f"vm-{i}",
                "status": "active",
            }
        )

    with pytest.raises(HTTPException) as exc:
        assert_org_vm_quota(org_id)
    assert exc.value.status_code == 403


def test_backfill_org_resources_script(db):
    from datetime import datetime
    from bson import ObjectId

    org_id = str(ObjectId())
    db["organizations"].insert_one(
        {"_id": ObjectId(org_id), "name": "Backfill Org", "owner_username": "bf_owner"}
    )
    db["organization_members"].insert_one(
        {"org_id": org_id, "username": "bf_owner", "role": "owner", "joined_at": datetime.utcnow()}
    )
    db["vm_assignments"].insert_one(
        {
            "assignment_id": "assign_bf",
            "user_id": "bf_owner",
            "vm_name": "vm-bf",
            "status": "active",
        }
    )

    from scripts.backfill_org_resources import backfill_collection

    updated = backfill_collection("vm_assignments", "user_id")
    assert updated == 1
    doc = db["vm_assignments"].find_one({"assignment_id": "assign_bf"})
    assert doc["org_id"] == org_id
    assert doc["created_by"] == "bf_owner"
