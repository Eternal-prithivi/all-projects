# =============================================================================
# MODULE: provision/boto3_deployer.py
# PURPOSE: Thin exports for boto3 provisioning (implementation in boto3_composer.py).
# USED BY: routes_provision.py when user Settings → Boto3 engine.
# =============================================================================
from __future__ import annotations

from app.provision.boto3_composer import (
    BOTO3_IMPLEMENTED,
    apply_fast,
    boto3_can_handle,
    destroy_fast,
    enabled_modules,
    plan_fast,
)

# Legacy name — same as boto3_can_handle()[0] for simple template-only checks
def is_fast_path_config(config: dict) -> bool:
    ok, _ = boto3_can_handle(config)
    return ok


__all__ = [
    "BOTO3_IMPLEMENTED",
    "apply_fast",
    "boto3_can_handle",
    "destroy_fast",
    "enabled_modules",
    "is_fast_path_config",
    "plan_fast",
]
