from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.security.security_stale_tasks import run_security_stale_check


@patch("app.security.security_stale_tasks.get_database")
@patch("app.security.security_stale_tasks.get_user_security_preferences")
@patch("app.security.security_stale_tasks.notify_stale_file_pending")
def test_run_security_stale_check_notifies(mock_notify, mock_prefs, mock_db):
    mock_prefs.return_value = {"stale_file_days": 90, "stale_notice_days": 7}
    now = datetime.now(timezone.utc)
    stale_file = {
        "_id": "1",
        "owner_username": "alice",
        "filename": "old.pem",
        "upload_date": now - timedelta(days=120),
        "last_accessed_at": now - timedelta(days=120),
        "vault_status": "active",
        "awaiting_encryption_choice": False,
    }
    secure_files = MagicMock()
    secure_files.distinct.return_value = ["alice"]
    secure_files.find.return_value = [stale_file]
    db = {"secure_files": secure_files}
    mock_db.return_value = db

    result = run_security_stale_check()
    assert result["success"] is True
    mock_notify.assert_called_once()
