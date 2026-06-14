"""Unit tests for BYOC → Terraform env resolution."""

from unittest.mock import patch

from app.provision.byoc_credentials import (
    resolve_byoc_terraform_env,
    terraform_env_to_api_credentials,
)


@patch("app.byoc.credential_resolver.resolve_aws_credentials", return_value={})
def test_terraform_env_empty_when_no_byoc(_mock_resolve):
    assert resolve_byoc_terraform_env("nobody") == {}


@patch("app.byoc.credential_resolver.resolve_aws_credentials")
def test_access_keys_mapped_to_env(mock_resolve):
    mock_resolve.return_value = {
        "access_key_id": "AKIA123",
        "secret_access_key": "secret",
        "region": "eu-west-1",
    }
    env = resolve_byoc_terraform_env("alice", "ap-south-1")
    assert env["AWS_ACCESS_KEY_ID"] == "AKIA123"
    assert env["AWS_SECRET_ACCESS_KEY"] == "secret"
    assert env["AWS_DEFAULT_REGION"] == "eu-west-1"


def test_api_credentials_roundtrip():
    env = {
        "AWS_ACCESS_KEY_ID": "AKIA",
        "AWS_SECRET_ACCESS_KEY": "sec",
        "AWS_SESSION_TOKEN": "tok",
    }
    api = terraform_env_to_api_credentials(env)
    assert api["access_key_id"] == "AKIA"
    assert api["session_token"] == "tok"
