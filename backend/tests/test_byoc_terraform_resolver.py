"""BYOC Terraform env resolution for tri-cloud."""

from unittest.mock import patch

from app.byoc.credential_resolver import resolve_credentials


@patch("app.provision.byoc_credentials.resolve_byoc_terraform_env")
def test_resolve_credentials_aws(mock_env):
    mock_env.return_value = {
        "AWS_ACCESS_KEY_ID": "AKIA",
        "AWS_SECRET_ACCESS_KEY": "secret",
    }
    creds = resolve_credentials("user1", "aws")
    assert creds["access_key_id"] == "AKIA"


@patch("app.provision.byoc_credentials.resolve_gcp_terraform_env")
def test_resolve_credentials_gcp(mock_env):
    mock_env.return_value = {
        "GOOGLE_CREDENTIALS": '{"type": "service_account"}',
        "GOOGLE_PROJECT": "proj-1",
    }
    creds = resolve_credentials("user1", "GCP")
    assert creds["project_id"] == "proj-1"


@patch("app.provision.byoc_credentials.resolve_azure_terraform_env")
def test_resolve_credentials_azure(mock_env):
    mock_env.return_value = {
        "ARM_CLIENT_ID": "cid",
        "ARM_CLIENT_SECRET": "sec",
        "ARM_SUBSCRIPTION_ID": "sub",
        "ARM_TENANT_ID": "tid",
    }
    creds = resolve_credentials("user1", "azure")
    assert creds["client_id"] == "cid"


@patch("app.provision.byoc_credentials.resolve_gcp_terraform_env", return_value={})
def test_resolve_credentials_gcp_missing_returns_none(_mock):
    assert resolve_credentials("user1", "gcp") is None
