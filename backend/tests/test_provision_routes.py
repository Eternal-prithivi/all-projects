"""API tests for provision policy-rules endpoint."""

from unittest.mock import MagicMock, patch

from app.provision.policy_checker import get_yaml_rules


def test_get_yaml_rules_non_empty():
    rules = get_yaml_rules()
    assert len(rules) >= 8


@patch("app.provision.routes_provision.get_yaml_rules")
def test_policy_rules_endpoint_shape(mock_rules):
    from app.provision.routes_provision import list_policy_rules

    mock_rules.return_value = [{"name": "test_rule", "severity": "block"}]
    user = MagicMock(username="u1")

    import asyncio
    result = asyncio.run(list_policy_rules(user=user))
    assert result["count"] == 1
    assert result["rules"][0]["name"] == "test_rule"
