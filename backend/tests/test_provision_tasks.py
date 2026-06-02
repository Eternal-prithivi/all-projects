"""Unit tests for scheduled drift Celery task (BYOC gating, mocked DB)."""

from unittest.mock import MagicMock, patch

from app.provision.models import DeploymentStatus, DriftReport, DriftStatus
from app.provision.tasks import scheduled_drift_check


@patch("app.config.demo_mode.is_demo_mode", return_value=False)
@patch("app.database.mongo_client.get_database")
@patch("app.provision.drift_detector.detect_drift")
@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_scheduled_drift_uses_owner_byoc(mock_byoc, mock_detect, mock_get_db, _mock_demo):
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


@patch("app.config.demo_mode.is_demo_mode", return_value=False)
@patch("app.database.mongo_client.get_database")
@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_scheduled_drift_skips_without_byoc(mock_byoc, mock_get_db, _mock_demo):
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


@patch("app.config.demo_mode.is_demo_mode", return_value=False)
@patch("app.database.mongo_client.get_database")
@patch("app.provision.boto3_drift.detect_drift_boto3")
@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_scheduled_drift_uses_boto3_for_boto3_deployments(mock_byoc, mock_boto3_drift, mock_get_db, _mock_demo):
    mock_byoc.return_value = {
        "AWS_ACCESS_KEY_ID": "AKIATEST",
        "AWS_SECRET_ACCESS_KEY": "secret",
        "AWS_DEFAULT_REGION": "ap-south-1",
    }
    mock_boto3_drift.return_value = DriftReport(
        status=DriftStatus.CLEAN,
        changes_detected=0,
        details=["ok"],
    )

    collection = MagicMock()
    collection.find.return_value = [
        {
            "deployment_name": "alice-boto3",
            "terraform_workspace": "boto3",
            "provision_engine": "boto3",
            "boto3_context": {"bucket_name": "my-bucket"},
            "user_id": "alice",
            "config": {"aws_region": "ap-south-1", "enable_s3": True, "bucket_name": "my-bucket"},
            "status": DeploymentStatus.DEPLOYED,
        }
    ]
    mock_get_db.return_value = {"provision_deployments": collection}

    result = scheduled_drift_check()

    mock_boto3_drift.assert_called_once()
    assert result["checked"] == 1
    assert result["skipped"] == 0


@patch("app.config.demo_mode.is_demo_mode", return_value=False)
@patch("app.database.mongo_client.get_database")
@patch("app.provision.drift_detector.detect_drift")
@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_scheduled_drift_skips_terraform_without_workspace(mock_byoc, mock_detect, mock_get_db, _mock_demo):
    mock_byoc.return_value = {
        "AWS_ACCESS_KEY_ID": "AKIATEST",
        "AWS_SECRET_ACCESS_KEY": "secret",
    }

    collection = MagicMock()
    collection.find.return_value = [
        {
            "deployment_name": "legacy-tf",
            "terraform_workspace": "boto3",
            "provision_engine": "terraform",
            "user_id": "alice",
            "config": {"aws_region": "ap-south-1"},
            "status": DeploymentStatus.DEPLOYED,
        }
    ]
    mock_get_db.return_value = {"provision_deployments": collection}

    result = scheduled_drift_check()

    mock_detect.assert_not_called()
    assert result["skipped"] == 1
    assert result["checked"] == 0
