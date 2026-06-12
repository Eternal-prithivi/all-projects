"""Unit tests for plan entitlements and quota enforcement."""

import pytest
from fastapi import HTTPException

from app.payments.plan_entitlements import feature_upgrade_detail, require_feature
from app.payments.quota_service import assert_vm_quota, count_personal_vms


def test_free_plan_features():
    from app.payments.plan_entitlements import _features_for_plan

    f = _features_for_plan("free")
    assert f["live_billing"] is False
    assert f["byoc"] is False
    assert f["provision_policies"] is False
    assert f["api_access"] is False
    assert f["team_seat_billing"] is False
    assert f["ai_recommendations"] is False


def test_pro_plan_features():
    from app.payments.plan_entitlements import _features_for_plan

    f = _features_for_plan("pro")
    assert f["live_billing"] is True
    assert f["byoc"] is True
    assert f["provision_policies"] is True
    assert f["api_access"] is True
    assert f["team_seat_billing"] is True
    assert f["ai_recommendations"] is True


def test_require_feature_raises_for_free(monkeypatch):
    monkeypatch.setattr(
        "app.payments.plan_entitlements.get_effective_plan_id",
        lambda _u: "free",
    )
    with pytest.raises(HTTPException) as exc:
        require_feature("alice", "byoc")
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert detail["code"] == "plan_feature_locked"
    assert detail["upgrade_required"] is True
    assert detail["min_plan"] == "pro"


def test_feature_upgrade_detail():
    meta = feature_upgrade_detail("api_access")
    assert meta["min_plan"] == "pro"
    assert meta["min_plan_name"] == "Pro"


def test_personal_vm_quota(db, monkeypatch):
    from app.payments.subscription_service import apply_user_plan_limits

    username = "quota_solo_user"
    db["users"].insert_one({"username": username, "email": f"{username}@test.com"})
    apply_user_plan_limits(username, "free")

    db["vm_assignments"].insert_many(
        [
            {
                "assignment_id": "a1",
                "user_id": username,
                "vm_name": "vm-1",
                "status": "active",
            },
            {
                "assignment_id": "a2",
                "user_id": username,
                "vm_name": "vm-2",
                "status": "active",
            },
        ]
    )

    assert count_personal_vms(username) == 2

    monkeypatch.setattr(
        "app.organizations.resource_acl.get_org_context",
        lambda _u: None,
    )
    monkeypatch.setattr(
        "app.payments.quota_service.get_org_context",
        lambda _u: None,
    )

    with pytest.raises(HTTPException) as exc:
        assert_vm_quota(username)
    assert exc.value.status_code == 403
