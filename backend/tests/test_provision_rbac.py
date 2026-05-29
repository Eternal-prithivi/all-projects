"""Unit tests for provision RBAC (mocked MongoDB role assignments)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.provision.rbac import (
    ProvisionAction,
    ProvisionRole,
    assign_provision_role,
    check_permission,
    get_user_provision_role,
)


def _user(username: str, role: str = "user"):
    return SimpleNamespace(username=username, role=role)


@patch("app.provision.rbac._get_roles_collection")
def test_explicit_devops_role_can_apply(mock_coll):
    mock_coll.return_value.find_one.return_value = {"role": ProvisionRole.DEVOPS}
    user = _user("ops1")
    allowed, _ = check_permission(user, ProvisionAction.APPLY)
    assert allowed is True


@patch("app.provision.rbac._get_roles_collection")
def test_default_developer_cannot_apply(mock_coll):
    mock_coll.return_value.find_one.return_value = None
    user = _user("dev1")
    allowed, msg = check_permission(user, ProvisionAction.APPLY)
    assert allowed is False
    assert "not permitted" in msg.lower()


@patch("app.provision.rbac._get_roles_collection")
def test_zenith_admin_maps_to_provision_admin(mock_coll):
    mock_coll.return_value.find_one.return_value = None
    user = _user("admin1", role="admin")
    assert get_user_provision_role(user) == ProvisionRole.ADMIN
    allowed, _ = check_permission(user, ProvisionAction.DESTROY)
    assert allowed is True


@patch("app.provision.rbac._get_roles_collection")
def test_viewer_plan_denied(mock_coll):
    mock_coll.return_value.find_one.return_value = {"role": ProvisionRole.VIEWER}
    user = _user("viewer1")
    allowed, _ = check_permission(user, ProvisionAction.PLAN)
    assert allowed is False


@patch("app.provision.rbac._get_roles_collection")
def test_assign_provision_role_upserts(mock_coll):
    collection = MagicMock()
    mock_coll.return_value = collection
    result = assign_provision_role("newdev", ProvisionRole.DEVELOPER, "admin1")
    assert result["username"] == "newdev"
    assert result["role"] == ProvisionRole.DEVELOPER
    collection.update_one.assert_called_once()
