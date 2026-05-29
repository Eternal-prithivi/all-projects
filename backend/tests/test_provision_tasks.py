"""Unit tests for scheduled drift Celery task (BYOC gating, mocked DB)."""

from unittest.mock import MagicMock, patch

from app.provision.models import DeploymentStatus, DriftReport, DriftStatus
from app.provision.tasks import scheduled_drift_check


@patch("app.database.mongo_client.get_database")
@patch("app.provision.drift_detector.detect_drift")
@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_scheduled_drift_uses_owner_byoc(mock_byoc, mock_detect, mock_get_db):
    mock_byoc.return_value = {
        "AWS_ACCESS_KEY_ID": "AKIATEST",
        "AWS_SECRET_ACCESS_KEY": "secret",
        "AWS_DEFAULT_REGION": "ap-south-1",
    }
    mock_detect.return_value = DriftReport(
        status=DriftStatus.CLEAN,
        changes_detected=0,
        details=["ok"],
    )

    collection = MagicMock()
    collection.find.return_value = [
        {
            "deployment_name": "alice-123",
            "terraform_workspace": "/tmp/ws",
            "user_id": "alice",
            "config": {"aws_region": "ap-south-1"},
            "status": DeploymentStatus.DEPLOYED,
        }
    ]
    mock_get_db.return_value = {"provision_deployments": collection}

    result = scheduled_drift_check()

    mock_byoc.assert_called_once_with("alice", "ap-south-1")
    mock_detect.assert_called_once()
    assert result["checked"] == 1
    assert result["skipped"] == 0


@patch("app.database.mongo_client.get_database")
@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_scheduled_drift_skips_without_byoc(mock_byoc, mock_get_db):
    mock_byoc.return_value = {}

    collection = MagicMock()
    collection.find.return_value = [
        {
            "deployment_name": "bob-456",
            "terraform_workspace": "/tmp/ws2",
            "user_id": "bob",
            "config": {},
            "status": DeploymentStatus.DEPLOYED,
        }
    ]
    mock_get_db.return_value = {"provision_deployments": collection}

    result = scheduled_drift_check()

    assert result["checked"] == 0
    assert result["skipped"] == 1
    collection.update_one.assert_called_once()
