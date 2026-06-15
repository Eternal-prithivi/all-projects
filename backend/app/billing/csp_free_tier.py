"""
CSP-aligned free tier limits for platform-key usage.

When users run on Zenith platform credentials (not BYOC), free plan quotas
mirror typical cloud provider free-tier ceilings per user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List


@dataclass(frozen=True)
class CspFreeTierLimits:
    max_storage_gb: int
    max_concurrent_vms: int
    max_vm_hours_per_month: int
    allowed_vm_skus: FrozenSet[str]
    provision_allowed_modules: FrozenSet[str]
    terraform_on_platform: bool


CSP_FREE_TIER: Dict[str, CspFreeTierLimits] = {
    "AWS": CspFreeTierLimits(
        max_storage_gb=5,
        max_concurrent_vms=1,
        max_vm_hours_per_month=750,
        allowed_vm_skus=frozenset({"t2.micro", "t3.micro"}),
        provision_allowed_modules=frozenset({"s3", "dynamodb"}),
        terraform_on_platform=False,
    ),
    "GCP": CspFreeTierLimits(
        max_storage_gb=5,
        max_concurrent_vms=1,
        max_vm_hours_per_month=750,
        allowed_vm_skus=frozenset({"e2-micro", "f1-micro"}),
        provision_allowed_modules=frozenset({"gcs", "firestore"}),
        terraform_on_platform=False,
    ),
    "Azure": CspFreeTierLimits(
        max_storage_gb=5,
        max_concurrent_vms=1,
        max_vm_hours_per_month=750,
        allowed_vm_skus=frozenset({"Standard_B1s", "Standard_B1ms"}),
        provision_allowed_modules=frozenset({"azure_storage", "cosmos"}),
        terraform_on_platform=False,
    ),
}

# Zenith free plan defaults (most restrictive across CSPs for org-wide caps)
FREE_PLAN_VM_LIMIT = 1
FREE_PLAN_STORAGE_GB = 5


def is_free_platform_plan(plan_id: str) -> bool:
    return (plan_id or "free").lower() == "free"


def free_tier_limits_for_csp(csp: str) -> CspFreeTierLimits:
    from app.cloud.providers import normalize_provider

    key = normalize_provider(csp or "AWS")
    return CSP_FREE_TIER.get(key, CSP_FREE_TIER["AWS"])


def free_tier_vm_sku_allowed(csp: str, sku: str) -> bool:
    limits = free_tier_limits_for_csp(csp)
    normalized = (sku or "").strip().lower()
    return any(allowed.lower() in normalized or normalized in allowed.lower() for allowed in limits.allowed_vm_skus)


def free_tier_provision_module_allowed(module_key: str) -> bool:
    key = (module_key or "").lower().replace("enable_", "")
    aliases = {
        "s3": "s3",
        "gcs": "gcs",
        "azure_storage": "azure_storage",
        "dynamodb": "dynamodb",
        "firestore": "firestore",
        "cosmos": "cosmos",
    }
    canonical = aliases.get(key, key)
    allowed: List[str] = []
    for lim in CSP_FREE_TIER.values():
        allowed.extend(lim.provision_allowed_modules)
    return canonical in set(allowed)
