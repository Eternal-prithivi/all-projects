"""Org-scoped resource access control."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from app.organizations import service as org_service

Action = Literal["read", "write", "delete"]


def get_org_context(username: str) -> Optional[Dict[str, Any]]:
    m = org_service.get_membership(username)
    if not m:
        return None
    return {
        "org_id": m["org_id"],
        "role": m.get("role"),
        "username": username,
        "is_admin": m.get("role") in ("owner", "admin"),
    }


def org_tags_for_create(username: str) -> Dict[str, Any]:
    """Fields to set on new resources."""
    ctx = get_org_context(username)
    if not ctx:
        return {}
    return {"org_id": ctx["org_id"], "created_by": username}


def list_filter_for_user(
    username: str,
    *,
    user_field: str = "user_id",
    owner_field: str = "owner_username",
    admin_sees_all: bool = True,
) -> Dict[str, Any]:
    """
    Mongo filter for listing resources.
    Solo users: filter by user_field / owner_field.
    Org admins: all org resources when admin_sees_all.
    Org members: own resources only (by created_by or legacy user field).
    """
    ctx = get_org_context(username)
    if not ctx:
        return {"$or": [{user_field: username}, {owner_field: username}]}

    org_id = ctx["org_id"]
    if ctx["is_admin"] and admin_sees_all:
        return {
            "$or": [
                {"org_id": org_id},
                {user_field: username},
                {owner_field: username},
            ]
        }

    return {
        "$or": [
            {"org_id": org_id, "created_by": username},
            {"org_id": org_id, user_field: username},
            {"org_id": {"$exists": False}, user_field: username},
            {"org_id": {"$exists": False}, owner_field: username},
        ]
    }


def can_access_resource(
    username: str,
    doc: Dict[str, Any],
    action: Action,
    *,
    user_field: str = "user_id",
    owner_field: str = "owner_username",
) -> bool:
    if not doc:
        return False

    ctx = get_org_context(username)
    doc_org = doc.get("org_id")
    created_by = doc.get("created_by") or doc.get(user_field) or doc.get(owner_field)

    if not ctx:
        return username in (doc.get(user_field), doc.get(owner_field))

    if doc_org and doc_org != ctx["org_id"]:
        return False

    if ctx["is_admin"]:
        return True

    if action == "read":
        return created_by == username or doc.get(user_field) == username

    return created_by == username or doc.get(user_field) == username


def count_member_resources(org_id: str, username: str) -> Dict[str, int]:
    from app.database.mongo_client import get_database

    db = get_database()
    vm = db["vm_assignments"].count_documents({"org_id": org_id, "created_by": username})
    vm += db["vm_assignments"].count_documents(
        {"org_id": org_id, "user_id": username, "created_by": {"$exists": False}}
    )
    prov = db["provision_deployments"].count_documents({"org_id": org_id, "created_by": username})
    prov += db["provision_deployments"].count_documents(
        {"org_id": org_id, "user_id": username, "created_by": {"$exists": False}}
    )
    files = db["files"].count_documents({"org_id": org_id, "created_by": username})
    files += db["files"].count_documents(
        {"org_id": org_id, "owner_username": username, "created_by": {"$exists": False}}
    )
    return {"vms": vm + prov, "files": files}
