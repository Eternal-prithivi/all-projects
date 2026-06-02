"""Tests for per-user built-in policy overrides."""

import pytest

from app.provision.policy_checker import evaluate_yaml_policies, get_merged_rules
from app.provision.policy_overrides import (
    delete_override,
    upsert_override,
)
from app.database.mongo_client import get_database

COLLECTION = "provision_policy_overrides"


@pytest.fixture
def username():
    return "policy_override_test_user"


@pytest.fixture(autouse=True)
def cleanup(username):
    get_database()[COLLECTION].delete_many({"username": username})
    yield
    get_database()[COLLECTION].delete_many({"username": username})


def test_disable_builtin_excludes_from_eval(username):
    upsert_override(username, "expensive_ec2_instance", enabled=False)
    config = {
        "instance_type": "m5.large",
        "enable_ec2": True,
        "enable_vpc": True,
        "tags": {"Owner": "x"},
    }
    result = evaluate_yaml_policies(config, username=username)
    assert not any(v.rule_name == "expensive_ec2_instance" for v in result.warnings)


def test_customize_builtin_severity(username):
    upsert_override(
        username,
        "expensive_ec2_instance",
        severity="block",
        enabled=True,
    )
    config = {
        "instance_type": "m5.large",
        "enable_ec2": True,
        "enable_vpc": True,
        "tags": {"Owner": "x"},
    }
    result = evaluate_yaml_policies(config, username=username)
    assert any(v.rule_name == "expensive_ec2_instance" for v in result.blocks)
    assert not result.can_deploy


def test_reset_override(username):
    upsert_override(username, "expensive_ec2_instance", enabled=False)
    assert delete_override(username, "expensive_ec2_instance")
    merged = get_merged_rules(username)
    rule = next(r for r in merged if r["name"] == "expensive_ec2_instance")
    assert rule["source"] == "builtin"
    assert rule.get("is_customized") is False
