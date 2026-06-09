from unittest.mock import MagicMock, patch  # noqa: F401 — patch used by decorators

from app.security.security_service import apply_vault_action, notify_encryption_pending


@patch("app.security.security_service.notification_service.create_notification")
def test_notify_encryption_pending(mock_create):
    mock_create.return_value = "nid"
    nid = notify_encryption_pending("alice", "secret.txt", ["credential_keywords"])
    assert nid == "nid"
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["metadata"]["category"] == "security_encryption_pending"


def test_apply_vault_action_snooze_stale():
    files_db = MagicMock()
    files_db.find_one.return_value = {"_id": "abc", "filename": "f.txt"}
    result = apply_vault_action(files_db, "alice", "f.txt", "snooze_stale")
    assert result["ok"] is True
    files_db.update_one.assert_called_once()


@patch("app.security.security_service.archive_secure_vault_object", return_value="zenith-secure-gcp-replica")
@patch("app.security.security_service.resolve_secure_storage")
def test_apply_vault_action_archive(mock_resolve, mock_archive):
    files_db = MagicMock()
    storage = MagicMock()
    storage.object_key.return_value = "alice/f.txt"
    mock_resolve.return_value = storage
    files_db.find_one.return_value = {"_id": "abc", "filename": "f.txt", "csp": "GCP"}
    result = apply_vault_action(files_db, "alice", "f.txt", "archive")
    assert result["vault_status"] == "archived"
    assert result["cloud_bucket"] == "zenith-secure-gcp-replica"
    mock_archive.assert_called_once()


@patch("app.security.security_service.restore_secure_vault_object", return_value="zenith-secure-gcp")
@patch("app.security.security_service.resolve_secure_storage")
def test_apply_vault_action_restore(mock_resolve, mock_restore):
    files_db = MagicMock()
    storage = MagicMock()
    storage.object_key.return_value = "alice/f.txt"
    mock_resolve.return_value = storage
    files_db.find_one.return_value = {
        "_id": "abc",
        "filename": "f.txt",
        "vault_status": "archived",
        "csp": "GCP",
    }
    result = apply_vault_action(files_db, "alice", "f.txt", "restore")
    assert result["ok"] is True
    assert result["vault_status"] == "active"
    mock_restore.assert_called_once()
