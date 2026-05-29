"""Ensure storage upload path uses BYOC-resolved buckets, not platform settings."""

from unittest.mock import MagicMock, patch

from app.storage import uploader


@patch("app.storage.uploader.build_aws_s3_client")
def test_upload_to_aws_uses_resolved_bucket(mock_build_client):
    mock_client = MagicMock()
    mock_build_client.return_value = (mock_client, "user-byoc-bucket", True)

    file_mock = MagicMock()
    file_mock.file = MagicMock()

    key = uploader.upload_to_aws(file_mock, "alice", "report.csv", "S3 Standard")

    assert key == "alice/report.csv"
    mock_client.upload_fileobj.assert_called_once()
    args, kwargs = mock_client.upload_fileobj.call_args
    assert args[1] == "user-byoc-bucket"
    assert args[2] == "alice/report.csv"
    mock_build_client.assert_called_once_with("alice")
