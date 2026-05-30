# =============================================================================
# MODULE: provision/boto3_deployer.py
# PURPOSE: Boto3 provisioning entry points (delegates to boto3_composer).
# USED BY: routes_provision.py when provision_engine == boto3
# =============================================================================
from __future__ import annotations

from typing import Any

from app.provision.boto3_composer import (
    BOTO3_SUPPORTED_MODULES,
    boto3_can_handle,
    enabled_modules,
    plan_composed,
    apply_composed,
    destroy_composed,
)

# Backward-compatible aliases
FAST_PATH_TEMPLATES = {"static-site", "serverless-db"}


def is_fast_path_config(config: dict) -> bool:
    """True when boto3 composer can handle all enabled modules."""
    ok, _ = boto3_can_handle(config)
    return ok


def plan_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    return plan_composed(config, aws_creds)


def apply_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    return apply_composed(config, aws_creds)


def destroy_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    return destroy_composed(config, aws_creds)


__all__ = [
    "BOTO3_SUPPORTED_MODULES",
    "FAST_PATH_TEMPLATES",
    "boto3_can_handle",
    "enabled_modules",
    "is_fast_path_config",
    "plan_fast",
    "apply_fast",
    "destroy_fast",
]
