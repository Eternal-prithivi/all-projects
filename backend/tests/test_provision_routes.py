"""API tests for provision policy-rules endpoint."""

from unittest.mock import MagicMock, patch

from app.provision.policy_checker import get_yaml_rules


def test_get_yaml_rules_non_empty():
    rules = get_yaml_rules()
    assert len(rules) >= 8


@patch("app.provision.routes_provision.get_merged_rules")
@patch("app.provision.routes_provision.get_yaml_rules")
def test_policy_rules_endpoint_shape(mock_yaml, mock_merged):
    from app.provision.routes_provision import list_policy_rules

    mock_yaml.return_value = [{"name": "builtin_rule", "severity": "block"}]
    mock_merged.return_value = [
        {"name": "builtin_rule", "severity": "block", "source": "builtin"},
        {"name": "custom_rule", "severity": "warning", "source": "custom", "id": "abc"},
    ]
    user = MagicMock(username="u1")

    import asyncio
    result = asyncio.run(list_policy_rules(user=user))
    assert result["count"] == 2
    assert result["builtin_count"] == 1
    assert result["custom_count"] == 1
    assert result["rules"][1]["name"] == "custom_rule"
