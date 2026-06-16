"""Safe evaluation of provision policy conditions (no eval)."""

from __future__ import annotations

from typing import Any

from simpleeval import EvalWithCompoundTypes


_ALLOWED_FUNCTIONS = {"int": int, "len": len}


def evaluate_condition(condition: str, policy_dict: dict[str, Any]) -> bool:
    """Evaluate a YAML/custom policy condition against a policy context dict."""
    evaluator = EvalWithCompoundTypes(functions=_ALLOWED_FUNCTIONS)
    evaluator.names = dict(policy_dict)
    return bool(evaluator.eval(condition))


def validate_condition_syntax(condition: str, policy_dict: dict[str, Any] | None = None) -> str | None:
    """Return error message if condition cannot be parsed/evaluated."""
    sample = policy_dict or {
        "csp": "AWS",
        "s3_bucket_public": False,
        "ssh_open_to_world": False,
        "rdp_open_to_world": False,
        "iam_wildcard": False,
        "instance_type": "t2.micro",
        "s3_encryption": True,
        "tags": {},
        "cloudtrail_enabled": False,
        "environment": "free-tier",
        "enable_s3": False,
        "bucket_name": "",
        "budget_limit": "1",
        "enable_cloudwatch": False,
        "enable_ec2": False,
        "vm_enabled": False,
        "storage_enabled": False,
        "monitoring_enabled": False,
        "network_enabled": False,
    }
    try:
        evaluate_condition(condition, sample)
        return None
    except Exception as exc:
        return str(exc)
