"""Tests for provision engine resolver and boto3 module coverage."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.provision.boto3_composer import boto3_can_handle, enabled_modules
from app.provision.engine_resolver import (
    get_user_provision_engine,
    resolve_provision_engine,
    deployment_engine,
)


def test_enabled_modules_static_site():
    config = {
        "enable_s3": True,
        "enable_ec2": False,
        "enable_vpc": False,
        "enable_dynamodb": False,
    }
    assert enabled_modules(config) == {"s3"}


def test_boto3_can_handle_backend_app():
    config = {
        "enable_vpc": True,
        "enable_ec2": True,
        "enable_iam": True,
        "enable_cloudwatch": True,
        "enable_s3": False,
        "enable_dynamodb": False,
    }
    ok, unsupported = boto3_can_handle(config)
    assert ok is True
    assert unsupported == set()


def test_boto3_cannot_ec2_without_vpc():
    config = {"enable_ec2": True, "enable_vpc": False}
    ok, unsupported = boto3_can_handle(config)
    assert ok is False
    assert "ec2" in unsupported


@patch("app.provision.engine_resolver.get_database")
def test_get_user_provision_engine_default(mock_db):
    mock_db.return_value = MagicMock()
    mock_db.return_value.__getitem__.return_value.find_one.return_value = {}
    assert get_user_provision_engine("user1") == "boto3"


@patch("app.provision.engine_resolver.get_database")
def test_get_user_provision_engine_terraform(mock_db):
    mock_db.return_value = MagicMock()
    mock_db.return_value.__getitem__.return_value.find_one.return_value = {
        "settings": {"preferences": {"provision_engine": "terraform"}}
    }
    assert get_user_provision_engine("user1") == "terraform"


@patch("app.provision.engine_resolver.check_terraform_installed", return_value=True)
@patch("app.provision.engine_resolver.get_user_provision_engine", return_value="terraform")
def test_resolve_terraform_static_site(_pref, _tf):
    config = {"enable_s3": True, "template": "static-site"}
    assert resolve_provision_engine("u", config) == "terraform"


@patch("app.provision.engine_resolver.get_user_provision_engine", return_value="boto3")
def test_resolve_boto3_static_site(_pref):
    config = {"enable_s3": True, "bucket_name": "my-bucket"}
    assert resolve_provision_engine("u", config) == "boto3"


@patch("app.provision.engine_resolver.get_user_provision_engine", return_value="boto3")
def test_resolve_boto3_rejects_billing(_pref):
    config = {"enable_s3": True, "enable_billing": True}
    with pytest.raises(HTTPException) as exc:
        resolve_provision_engine("u", config)
    assert exc.value.status_code == 400


def test_deployment_engine_legacy_fast_path():
    assert deployment_engine({"fast_path": True}) == "boto3"
    assert deployment_engine({"terraform_workspace": "/tmp/x"}) == "terraform"
    assert deployment_engine({"provision_engine": "terraform"}) == "terraform"
