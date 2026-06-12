"""Organization-level resource quotas."""

from __future__ import annotations

from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.organizations.billing import get_org_limits
from app.organizations.resource_acl import get_org_context
from app.payments.quota_service import (
    assert_storage_quota,
    assert_vm_quota,
    count_org_storage_bytes,
    count_org_vms,
)

DB = get_database()


def assert_org_vm_quota(org_id: str) -> None:
    limits = get_org_limits(org_id)
    current = count_org_vms(org_id)
    cap = limits.get("vm_limit", 2)
    if cap < 999 and current >= cap:
        raise HTTPException(
            status_code=403,
            detail=f"Organization VM limit reached ({current}/{cap}). Upgrade plan or remove resources.",
        )


def assert_org_storage_quota(org_id: str, additional_bytes: int = 0) -> None:
    limits = get_org_limits(org_id)
    cap_gb = float(limits.get("storage_gb", 10))
    cap_bytes = cap_gb * (1024**3)
    current = count_org_storage_bytes(org_id)
    if current + additional_bytes > cap_bytes:
        raise HTTPException(
            status_code=403,
            detail=f"Organization storage limit exceeded ({cap_gb} GB cap).",
        )


def maybe_assert_org_quotas(username: str, *, storage_bytes: int = 0) -> None:
    """Assert quotas for org members or solo users."""
    ctx = get_org_context(username)
    if ctx:
        assert_org_vm_quota(ctx["org_id"])
        if storage_bytes > 0:
            assert_org_storage_quota(ctx["org_id"], storage_bytes)
        return
    assert_vm_quota(username)
    if storage_bytes > 0:
        assert_storage_quota(username, storage_bytes)
