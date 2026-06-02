"""Tests for per-user custom provision policies."""

import pytest

from app.provision.policy_store import (
    create_custom_rule,
    delete_custom_rule,
    custom_rules_as_yaml_rules,
    update_custom_rule,
    validate_policy_condition,
)


@pytest.fixture
def username():
    return "policy_store_test_user"


@pytest.fixture(autouse=True)
def cleanup(username):
    from app.database.mongo_client import get_database
    coll = get_database()["provision_custom_policies"]
    coll.delete_many({"username": username})
    yield
    coll.delete_many({"username": username})


def test_validate_condition_rejects_unsafe():
    assert validate_policy_condition("__import__('os')") is not None


def test_create_and_list_custom_rule(username):
    rule = create_custom_rule(
        username,
        name="my_budget_cap",
        description="Budget above $5",
        severity="warning",
        condition="budget_limit is not None and int(budget_limit) > 5",
    )
    assert rule["source"] == "custom"
    assert rule["enabled"] is True

    yaml_rules = custom_rules_as_yaml_rules(username)
    assert len(yaml_rules) == 1
    assert yaml_rules[0]["name"] == "my_budget_cap"


def test_update_disable_and_delete(username):
    created = create_custom_rule(
        username,
        name="tag_rule",
        description="Require tags",
        severity="block",
        condition="tags is None or tags == {}",
    )
    updated = update_custom_rule(username, created["id"], enabled=False)
    assert updated["enabled"] is False
    assert custom_rules_as_yaml_rules(username) == []

    assert delete_custom_rule(username, created["id"]) is True
    assert custom_rules_as_yaml_rules(username) == []
