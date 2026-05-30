# =============================================================================
# MODULE: provision/boto3_composer.py
# PURPOSE: Orchestrate module-composed AWS deploys (handlers in boto3_modules/).
# Parity with backend/terraform/modules/* for plan/apply/destroy + drift checks.
# =============================================================================
from __future__ import annotations

import logging
from typing import Any, Optional

from app.provision.boto3_modules import billing, cloudwatch, dynamodb, ec2, iam, s3, vpc
from app.provision.boto3_modules.context import DeployContext

# Backward-compatible re-export
__all__ = [
    "BOTO3_IMPLEMENTED",
    "MODULE_FLAGS",
    "APPLY_ORDER",
    "DESTROY_ORDER",
    "DeployContext",
    "enabled_modules",
    "boto3_can_handle",
    "plan_composed",
    "apply_composed",
    "destroy_composed",
    "plan_fast",
    "apply_fast",
    "destroy_fast",
]

logger = logging.getLogger(__name__)

BOTO3_IMPLEMENTED = frozenset(
    {"s3", "dynamodb", "vpc", "ec2", "iam", "cloudwatch", "billing"}
)

MODULE_FLAGS: dict[str, str] = {
    "s3": "enable_s3",
    "dynamodb": "enable_dynamodb",
    "vpc": "enable_vpc",
    "ec2": "enable_ec2",
    "iam": "enable_iam",
    "cloudwatch": "enable_cloudwatch",
    "billing": "enable_billing",
}

APPLY_ORDER = ("vpc", "ec2", "iam", "cloudwatch", "s3", "dynamodb", "billing")
DESTROY_ORDER = ("billing", "dynamodb", "s3", "cloudwatch", "iam", "ec2", "vpc")

_PLAN_HANDLERS = {
    "s3": s3.plan_s3,
    "dynamodb": dynamodb.plan_dynamodb,
    "vpc": vpc.plan_vpc,
    "ec2": ec2.plan_ec2,
    "iam": iam.plan_iam,
    "cloudwatch": cloudwatch.plan_cloudwatch,
    "billing": billing.plan_billing,
}
_APPLY_HANDLERS = {
    "s3": s3.apply_s3,
    "dynamodb": dynamodb.apply_dynamodb,
    "vpc": vpc.apply_vpc,
    "ec2": ec2.apply_ec2,
    "iam": iam.apply_iam,
    "cloudwatch": cloudwatch.apply_cloudwatch,
    "billing": billing.apply_billing,
}
_DESTROY_HANDLERS = {
    "s3": s3.destroy_s3,
    "dynamodb": dynamodb.destroy_dynamodb,
    "vpc": vpc.destroy_vpc,
    "ec2": ec2.destroy_ec2,
    "iam": iam.destroy_iam,
    "cloudwatch": cloudwatch.destroy_cloudwatch,
    "billing": billing.destroy_billing,
}


def enabled_modules(config: dict) -> set[str]:
    out: set[str] = set()
    for mod, flag in MODULE_FLAGS.items():
        if config.get(flag):
            out.add(mod)
    return out


def boto3_can_handle(config: dict) -> tuple[bool, set[str]]:
    """Return (ok, unsupported_module_names)."""
    enabled = enabled_modules(config)
    unsupported: set[str] = set()
    if "ec2" in enabled and "vpc" not in enabled:
        unsupported.add("vpc")
    unsupported |= enabled - BOTO3_IMPLEMENTED
    return (len(unsupported) == 0 and len(enabled) > 0, unsupported)


def plan_composed(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    enabled = enabled_modules(config)
    order = [m for m in APPLY_ORDER if m in enabled]
    all_lines: list[str] = ["Plan (boto3 — direct AWS SDK):", ""]
    all_resources: list[str] = []
    for mod in order:
        result = _PLAN_HANDLERS[mod](config, aws_creds, region)
        if result.get("error"):
            return {
                "success": False,
                "output": "",
                "error": result["error"],
                "has_changes": False,
                "resources": [],
            }
        all_lines.extend(result.get("lines") or [])
        all_resources.extend(result.get("resources") or [])
    all_lines.extend(["", f"Plan: {len(all_resources)} resource(s) to add.", "", "✓ Ready to apply."])
    return {
        "success": True,
        "output": "\n".join(all_lines),
        "error": None,
        "has_changes": bool(all_resources),
        "resources": all_resources,
    }


def apply_composed(
    config: dict,
    aws_creds: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext.from_dict(existing_ctx)
    enabled = enabled_modules(config)
    order = [m for m in APPLY_ORDER if m in enabled]
    steps: list[str] = []
    for mod in order:
        result = _APPLY_HANDLERS[mod](config, aws_creds, region, ctx)
        steps.extend(result.get("steps") or [])
        if not result.get("success"):
            return {
                "success": False,
                "output": "\n".join(steps),
                "error": result.get("error"),
                "resources": [],
                "boto3_context": ctx.to_dict(),
            }
    steps.append("")
    steps.append("Deployment complete (boto3).")
    return {
        "success": True,
        "output": "\n".join(steps),
        "error": None,
        "resources": [],
        "boto3_context": ctx.to_dict(),
    }


def destroy_composed(
    config: dict,
    aws_creds: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext.from_dict(existing_ctx)
    enabled = enabled_modules(config)
    order = [m for m in DESTROY_ORDER if m in enabled]
    steps: list[str] = []
    for mod in order:
        result = _DESTROY_HANDLERS[mod](config, aws_creds, region, ctx)
        steps.extend(result.get("steps") or [])
        if not result.get("success"):
            return {"success": False, "output": "\n".join(steps), "error": result.get("error")}
    return {"success": True, "output": "\n".join(steps), "error": None}


def plan_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    return plan_composed(config, aws_creds)


def apply_fast(config: dict, aws_creds: dict[str, str], existing_ctx: Optional[dict] = None) -> dict[str, Any]:
    return apply_composed(config, aws_creds, existing_ctx)


def destroy_fast(
    config: dict,
    aws_creds: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    return destroy_composed(config, aws_creds, existing_ctx)
