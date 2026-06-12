"""VM release terminates instances in the assignment's region/zone."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.vm.manager import release_vm_assignment
from app.vm.models import AssignmentStatus


@patch("app.vm.manager.vm_assignments_collection")
@patch("app.organizations.resource_acl.can_access_resource", return_value=True)
@patch("app.vm.manager.vm_provider.cloud_configured", return_value=True)
@patch("app.vm.manager.vm_provider.delete_vm")
@patch("app.vm.manager.vm_provider.vm_zone", return_value="asia-south1-a")
@patch("app.vm.manager.vm_provider.vm_runtime_context")
def test_release_uses_assignment_region_and_zone(
    mock_runtime_ctx,
    mock_vm_zone,
    mock_delete,
    _mock_configured,
    _mock_acl,
    mock_collection,
):
    assignment = {
        "assignment_id": "assign_test123",
        "user_id": "demo_user",
        "vm_name": "general-vm-2",
        "status": AssignmentStatus.ACTIVE.value,
        "csp": "GCP",
        "platform_region_slug": "asia",
        "compute_zone": "asia-south1-a",
    }
    mock_collection.find_one.return_value = assignment
    mock_collection.count_documents.return_value = 1
    mock_runtime_ctx.return_value.__enter__ = MagicMock(return_value="GCP")
    mock_runtime_ctx.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.vm.manager.settings") as mock_settings:
        mock_settings.VM_DELETE_ON_IDLE = True
        result = release_vm_assignment("demo_user", "assign_test123")

    assert result["success"] is True
    assert result["vm_deleted"] is True
    mock_runtime_ctx.assert_called_once_with("demo_user", "GCP", "asia")
    mock_delete.assert_called_once_with("GCP", "general-vm-2", zone="asia-south1-a")
    mock_collection.update_one.assert_called_once()


@patch("app.vm.manager.vm_assignments_collection")
@patch("app.organizations.resource_acl.can_access_resource", return_value=True)
@patch("app.vm.manager.vm_provider.cloud_configured", return_value=True)
@patch("app.vm.manager.vm_provider.delete_vm")
@patch("app.vm.manager.vm_provider.vm_zone", return_value="europe-west1-b")
@patch("app.vm.manager.vm_provider.vm_runtime_context")
def test_release_orphan_cleans_cloud_vm_when_already_released(
    mock_runtime_ctx,
    mock_vm_zone,
    mock_delete,
    _mock_configured,
    _mock_acl,
    mock_collection,
):
    stale = {
        "assignment_id": "assign_orphan",
        "user_id": "demo_user",
        "vm_name": "general-vm-2",
        "status": AssignmentStatus.RELEASED.value,
        "csp": "GCP",
        "platform_region_slug": "europe",
    }

    def find_one(query):
        if query.get("status") == AssignmentStatus.ACTIVE.value:
            return None
        return stale

    mock_collection.find_one.side_effect = find_one
    mock_collection.count_documents.return_value = 0
    mock_runtime_ctx.return_value.__enter__ = MagicMock(return_value="GCP")
    mock_runtime_ctx.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.vm.manager.settings") as mock_settings:
        mock_settings.VM_DELETE_ON_IDLE = True
        result = release_vm_assignment("demo_user", "assign_orphan")

    assert result["success"] is True
    assert result["already_released"] is True
    assert result["vm_deleted"] is True
    mock_delete.assert_called_once_with("GCP", "general-vm-2", zone="europe-west1-b")
    mock_collection.update_one.assert_not_called()
