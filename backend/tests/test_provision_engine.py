"""Tests for Boto3 vs Terraform provision engine resolution."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.provision.boto3_composer import BOTO3_IMPLEMENTED, boto3_can_handle
from app.provision.engine_resolver import (
    DEFAULT_ENGINE,
    deployment_engine,
    get_user_provision_engine,
    resolve_provision_engine,
)


def _static_site_config():
    return {
        "template": "static-site",
        "aws_region": "ap-south-1",
        "enable_s3": True,
        "enable_vpc": False,
        "enable_ec2": False,
        "enable_iam": False,
        "enable_cloudwatch": False,
        "enable_dynamodb": False,
        "enable_billing": False,
    }


@patch("app.provision.engine_resolver.get_database")
def test_get_user_provision_engine_default(mock_db):
    mock_db.return_value["users"].find_one.return_value = None
    assert get_user_provision_engine("alice") == DEFAULT_ENGINE


@patch("app.provision.engine_resolver.get_database")
def test_get_user_provision_engine_terraform(mock_db):
    mock_db.return_value["users"].find_one.return_value = {
        "settings": {"preferences": {"provision_engine": "terraform"}}
    }
    assert get_user_provision_engine("alice") == "terraform"


@patch("app.provision.engine_resolver.get_database")
@patch("app.provision.engine_resolver.check_terraform_installed", return_value=True)
def test_resolve_boto3_for_static_site(mock_tf, mock_db):
    mock_db.return_value["users"].find_one.return_value = {
        "settings": {"preferences": {"provision_engine": "boto3"}}
    }
    assert resolve_provision_engine("alice", _static_site_config()) == "boto3"


@patch("app.provision.engine_resolver.get_database")
@patch("app.provision.engine_resolver.check_terraform_installed", return_value=True)
def test_resolve_terraform_when_preferred(mock_tf, mock_db):
    mock_db.return_value["users"].find_one.return_value = {
        "settings": {"preferences": {"provision_engine": "terraform"}}
    }
    assert resolve_provision_engine("alice", _static_site_config()) == "terraform"


@patch("app.provision.engine_resolver.get_database")
@patch("app.provision.engine_resolver.check_terraform_installed", return_value=False)
def test_resolve_terraform_without_cli_raises_503(mock_tf, mock_db):
    mock_db.return_value["users"].find_one.return_value = {
        "settings": {"preferences": {"provision_engine": "terraform"}}
    }
    with pytest.raises(HTTPException) as exc:
        resolve_provision_engine("alice", _static_site_config())
    assert exc.value.status_code == 503


@patch("app.provision.engine_resolver.get_database")
@patch("app.provision.engine_resolver.check_terraform_installed", return_value=True)
def test_resolve_boto3_with_billing_enabled(mock_tf, mock_db):
    mock_db.return_value["users"].find_one.return_value = {
        "settings": {"preferences": {"provision_engine": "boto3"}}
    }
    cfg = _static_site_config()
    cfg["enable_billing"] = True
    assert resolve_provision_engine("alice", cfg) == "boto3"


def test_boto3_can_handle_static_site():
    ok, unsupported = boto3_can_handle(_static_site_config())
    assert ok is True
    assert unsupported == set()


def test_boto3_implemented_modules_match_terraform_modules():
    assert BOTO3_IMPLEMENTED == frozenset(
        {"s3", "dynamodb", "vpc", "ec2", "iam", "cloudwatch", "billing"}
    )


@patch("app.provision.engine_resolver.check_terraform_installed", return_value=True)
def test_resolve_gcp_forces_terraform(mock_tf):
  cfg = {"csp": "GCP", "enable_gcs": True}
  assert resolve_provision_engine("alice", cfg, "GCP") == "terraform"


def test_deployment_engine_from_record():
    assert deployment_engine({"provision_engine": "boto3"}) == "boto3"
    assert deployment_engine({"fast_path": True}) == "boto3"
    assert deployment_engine({}) == "terraform"


@patch("app.provision.routes_provision.get_user_provision_engine", return_value="boto3")
@patch("app.provision.routes_provision.check_terraform_installed", return_value=False)
@patch("app.provision.routes_provision.get_yaml_rules", return_value=[])
def test_provisioning_status_includes_engine(mock_rules, mock_tf, mock_pref):
    from app.provision.routes_provision import provisioning_status

    user = MagicMock(username="u1")
    import asyncio

    result = asyncio.run(provisioning_status(user=user))
    assert result["user_provision_engine"] == "boto3"
    assert "billing" in result["boto3_supported_modules"]
    assert result["terraform_installed"] is False
