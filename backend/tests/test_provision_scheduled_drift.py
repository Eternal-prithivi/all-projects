"""Scheduled drift resolves credentials per CSP."""

from unittest.mock import MagicMock, patch

from app.provision.models import DriftStatus
from app.provision.tasks import scheduled_drift_check


@patch("app.database.mongo_client.get_database")
@patch("app.config.demo_mode.is_demo_mode", return_value=False)
@patch("app.provision.byoc_credentials.resolve_provision_terraform_env")
@patch("app.provision.tasks._run_scheduled_drift")
def test_scheduled_drift_gcp_credentials(mock_run, mock_resolve, mock_demo, mock_db):
    from app.provision.models import DriftReport

    mock_resolve.return_value = ({"GOOGLE_CREDENTIALS": "{}"}, None)
    mock_run.return_value = DriftReport(
        status=DriftStatus.CLEAN,
        changes_detected=0,
        details=["ok"],
    )
    collection = MagicMock()
    mock_db.return_value.__getitem__.return_value = collection
    collection.find.return_value = [
        {
            "deployment_name": "u1-1",
            "user_id": "u1",
            "status": "deployed",
            "config": {"csp": "GCP", "enable_gcs": True},
            "provision_engine": "sdk",
        }
    ]

    result = scheduled_drift_check()

    mock_resolve.assert_called_once()
    assert mock_resolve.call_args[0][1] == "GCP"
    assert result["checked"] == 1
