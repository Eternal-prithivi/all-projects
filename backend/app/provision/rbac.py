# =============================================================================
# MODULE: provision/rbac.py
# PURPOSE: Role-based access control for Terraform provisioning operations
# SOURCE: Adapted from aws-provision-using-terraform/team-management/team_engine.py
# USED BY: routes_provision.py (apply, destroy, remediate require elevated roles)
# STORES: provision_roles collection in MongoDB
# DO NOT:
#   - Allow any authenticated user to apply or destroy — require admin or devops role
#   - Skip role checks on the remediate endpoint — it runs terraform apply
# =============================================================================
"""
Provision RBAC — role-based access control for infrastructure operations.

Roles:
  - admin:    Full access — plan, apply, destroy, remediate, manage roles
  - devops:   plan, apply, destroy, remediate, view
  - developer: plan, view (cannot apply or destroy)
  - viewer:   view only (can see deployments but not trigger any operations)

Zenith's existing admin flag (user.role == "admin") is mapped to the admin
provision role automatically. Other users default to "developer" unless
explicitly assigned a provision role.
"""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.database.mongo_client import get_database

logger = logging.getLogger(__name__)


class ProvisionRole(str, Enum):
    """Provision-specific roles."""
    ADMIN = "admin"
    DEVOPS = "devops"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class ProvisionAction(str, Enum):
    """Actions that can be performed on provisioned infrastructure."""
    VIEW = "view"
    PLAN = "plan"
    APPLY = "apply"
    DESTROY = "destroy"
    REMEDIATE = "remediate"
    DRIFT_CHECK = "drift_check"
    MANAGE_ROLES = "manage_roles"


# Role → permitted actions mapping
ROLE_PERMISSIONS: dict[str, set[str]] = {
    ProvisionRole.ADMIN: {
        ProvisionAction.VIEW,
        ProvisionAction.PLAN,
        ProvisionAction.APPLY,
        ProvisionAction.DESTROY,
        ProvisionAction.REMEDIATE,
        ProvisionAction.DRIFT_CHECK,
        ProvisionAction.MANAGE_ROLES,
    },
    ProvisionRole.DEVOPS: {
        ProvisionAction.VIEW,
        ProvisionAction.PLAN,
        ProvisionAction.APPLY,
        ProvisionAction.DESTROY,
        ProvisionAction.REMEDIATE,
        ProvisionAction.DRIFT_CHECK,
    },
    ProvisionRole.DEVELOPER: {
        ProvisionAction.VIEW,
        ProvisionAction.PLAN,
        ProvisionAction.DRIFT_CHECK,
    },
    ProvisionRole.VIEWER: {
        ProvisionAction.VIEW,
    },
}


def _get_roles_collection():
    """Get the provision_roles MongoDB collection."""
    DB = get_database()
    return DB["provision_roles"]


def get_user_provision_role(user: Any) -> str:
    """
    Resolve a user's provision role.

    Priority:
    1. Explicit role in provision_roles collection
    2. Zenith admin flag → admin
    3. Default → developer (can plan but not apply)
    """
    # Check for explicit provision role assignment
    collection = _get_roles_collection()
    role_doc = collection.find_one({"username": user.username})
    if role_doc:
        return role_doc.get("role", ProvisionRole.DEVELOPER)

    # Check if user is a Zenith-level admin
    user_role = getattr(user, "role", None)
    if user_role == "admin":
        return ProvisionRole.ADMIN

    # Default to developer (can plan but not apply/destroy)
    return ProvisionRole.DEVELOPER


def check_permission(user: Any, action: str) -> tuple[bool, str]:
    """
    Check if a user has permission to perform a provision action.

    Args:
        user: Current user object (from get_current_user dependency).
        action: ProvisionAction value to check.

    Returns:
        (allowed, message) tuple.
    """
    role = get_user_provision_role(user)
    permissions = ROLE_PERMISSIONS.get(role, set())

    if action in permissions:
        return True, f"✅ {user.username} ({role}) allowed to {action}"

    return False, (
        f"❌ {user.username} ({role}) is not permitted to {action}. "
        f"Required role: {_minimum_role_for_action(action)}"
    )


def _minimum_role_for_action(action: str) -> str:
    """Return the least-privileged role that can perform the given action."""
    for role in [ProvisionRole.VIEWER, ProvisionRole.DEVELOPER, ProvisionRole.DEVOPS, ProvisionRole.ADMIN]:
        if action in ROLE_PERMISSIONS.get(role, set()):
            return role
    return ProvisionRole.ADMIN


def assign_provision_role(
    target_username: str,
    role: str,
    assigned_by: str,
) -> dict[str, Any]:
    """
    Assign or update a user's provision role.

    Only admins can call this (enforced at the route level).
    """
    if role not in [r.value for r in ProvisionRole]:
        raise ValueError(f"Invalid role: {role}. Must be one of: {[r.value for r in ProvisionRole]}")

    collection = _get_roles_collection()
    collection.update_one(
        {"username": target_username},
        {"$set": {
            "username": target_username,
            "role": role,
            "assigned_by": assigned_by,
            "updated_at": datetime.utcnow(),
        }},
        upsert=True,
    )

    logger.info(f"Provision role '{role}' assigned to {target_username} by {assigned_by}")
    return {
        "username": target_username,
        "role": role,
        "assigned_by": assigned_by,
    }


def list_role_assignments() -> list[dict[str, Any]]:
    """List all explicit provision role assignments."""
    collection = _get_roles_collection()
    docs = list(collection.find({}, {"_id": 0}))
    return docs


def get_user_permissions(user: Any) -> dict[str, Any]:
    """Get full permission breakdown for a user."""
    role = get_user_provision_role(user)
    permissions = ROLE_PERMISSIONS.get(role, set())

    return {
        "username": user.username,
        "provision_role": role,
        "permissions": sorted(list(permissions)),
        "can_plan": ProvisionAction.PLAN in permissions,
        "can_apply": ProvisionAction.APPLY in permissions,
        "can_destroy": ProvisionAction.DESTROY in permissions,
        "can_remediate": ProvisionAction.REMEDIATE in permissions,
    }
