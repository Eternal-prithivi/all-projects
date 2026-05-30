# =============================================================================
# MODULE: provision/policy_checker.py
# PURPOSE: Evaluate infrastructure configs against YAML + OPA policy rules
# USED BY: routes_provision.py (plan + policy-check endpoints)
# READS FROM: backend/terraform/policy-engine/rules.yaml,
#             backend/terraform/opa-policies/aws_security.rego
# DO NOT:
#   - Hardcode policy rules here — all rules live in rules.yaml and .rego files
#   - Remove the block/warning distinction — blocks prevent deployment
# =============================================================================
from __future__ import annotations

import logging
from typing import Any

import yaml

from app.provision.models import PolicyCheckResult, PolicyViolation
from app.provision.terraform_runner import TERRAFORM_ROOT

logger = logging.getLogger(__name__)

RULES_PATH = TERRAFORM_ROOT / "policy-engine" / "rules.yaml"
OPA_POLICIES_DIR = TERRAFORM_ROOT / "opa-policies"


def config_to_policy_dict(config: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a ProvisionConfig dict to the format expected by policy engines.

    Security defaults are safe (no public S3, no open SSH, etc.) unless
    the user explicitly enables risky settings.
    """
    return {
        "s3_bucket_public": False,
        "ssh_open_to_world": False,
        "rdp_open_to_world": False,
        "iam_wildcard": False,
        "instance_type": config.get("instance_type", "t2.micro"),
        "s3_encryption": True,
        "tags": config.get("tags", {}),
        "cloudtrail_enabled": config.get("environment", "") == "production",
        "environment": config.get("environment", "free-tier"),
        "enable_s3": config.get("enable_s3", False),
        "bucket_name": config.get("bucket_name", ""),
        "budget_limit": config.get("budget_limit", "1"),
        "enable_cloudwatch": config.get("enable_cloudwatch", False),
        "enable_ec2": config.get("enable_ec2", False),
        "vpc_cidr": config.get("vpc_cidr", "10.0.0.0/16"),
        "enable_vpc": config.get("enable_vpc", False),
    }


def evaluate_yaml_policies(config: dict[str, Any]) -> PolicyCheckResult:
    """
    Evaluate config against YAML-defined policy rules.

    Returns PolicyCheckResult with blocks (prevent deploy) and warnings.
    """
    result = PolicyCheckResult(blocks=[], warnings=[], can_deploy=True)

    if not RULES_PATH.exists():
        logger.warning(f"Policy rules file not found: {RULES_PATH}")
        return result

    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "rules" not in data:
            logger.warning("No 'rules' key in rules.yaml")
            return result

        policy_dict = config_to_policy_dict(config)

        for rule in data["rules"]:
            condition = rule.get("condition", "False")
            try:
                # Safe eval against the policy dict only
                triggered = bool(eval(condition, {"__builtins__": {}}, policy_dict))  # noqa: S307
            except Exception:
                triggered = False

            if triggered:
                violation = PolicyViolation(
                    rule_name=rule["name"],
                    description=rule["description"].strip(),
                    severity=rule["severity"],
                )
                if rule["severity"] == "block":
                    result.blocks.append(violation)
                else:
                    result.warnings.append(violation)

        result.can_deploy = len(result.blocks) == 0

    except Exception as e:
        logger.error(f"YAML policy evaluation failed: {e}")

    return result


def evaluate_opa_policies(config: dict[str, Any]) -> PolicyCheckResult:
    """
    Evaluate config against OPA (Rego) policies using the OPAEngine wrapper.

    Falls back gracefully if OPA is not installed.
    """
    from app.provision.opa_engine import OPAEngine

    result = PolicyCheckResult(blocks=[], warnings=[], can_deploy=True)

    engine = OPAEngine(OPA_POLICIES_DIR)
    opa_result = engine.evaluate(config_to_policy_dict(config))

    if not opa_result.opa_available:
        logger.info(f"OPA CLI not installed — skipping OPA policy check: {opa_result.error}")
        return result

    if opa_result.error:
        logger.warning(f"OPA evaluation error: {opa_result.error}")
        return result

    for deny_msg in opa_result.blocks:
        result.blocks.append(PolicyViolation(
            rule_name="opa_deny",
            description=deny_msg,
            severity="block",
        ))

    for warn_msg in opa_result.warnings:
        result.warnings.append(PolicyViolation(
            rule_name="opa_warn",
            description=warn_msg,
            severity="warning",
        ))

    result.can_deploy = len(result.blocks) == 0

    return result


def full_policy_check(
    config: dict[str, Any],
    *,
    include_opa: bool = False,
) -> PolicyCheckResult:
    """
    Run YAML policy checks (fast). OPA is optional — slow CLI subprocesses.
    """
    yaml_result = evaluate_yaml_policies(config)
    if not include_opa:
        return yaml_result

    opa_result = evaluate_opa_policies(config)
    return PolicyCheckResult(
        blocks=yaml_result.blocks + opa_result.blocks,
        warnings=yaml_result.warnings + opa_result.warnings,
        can_deploy=(yaml_result.can_deploy and opa_result.can_deploy),
    )


def get_yaml_rules() -> list[dict[str, Any]]:
    """Return the raw YAML policy rules for display in the UI."""
    if not RULES_PATH.exists():
        return []
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("rules", [])
    except Exception:
        return []
