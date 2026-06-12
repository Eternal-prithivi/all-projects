"""Discover and rank Azure VM sizes available for x64 Linux images."""

from __future__ import annotations

import re
from typing import Any

from app.provision.sdk_modules.common import azure_vm_sizes_to_try

# Cheaper x64 sizes first when probing a region via ResourceSkus API.
AZURE_VM_SIZE_PRIORITY: tuple[str, ...] = (
    "Standard_B1s",
    "Standard_B1ms",
    "Standard_B2s",
    "Standard_B2ms",
    "Standard_A1_v2",
    "Standard_A2_v2",
    "Standard_DS1_v2",
    "Standard_DS2_v2",
    "Standard_D2s_v3",
    "Standard_D2as_v4",
    "Standard_D2as_v5",
    "Standard_D2ads_v5",
    "Standard_F1s",
    "Standard_F2s",
    "Standard_F2s_v2",
)

# Arm-only burstable / Ampere naming patterns (x64 Ubuntu images won't work).
_ARM_SKU_RE = re.compile(
    r"(pts|pls|pds|pas|plds|als_v2|ats_v2|tps|ap_v2|_mp)",
    re.IGNORECASE,
)

MAX_VCPUS_DEFAULT = 4
MAX_SIZES_TO_TRY = 24


def _likely_arm_sku(name: str) -> bool:
    if _ARM_SKU_RE.search(name):
        return True
    return name.lower().endswith("_arm")


def _sku_vcpus(capabilities: dict[str, str]) -> int:
    raw = capabilities.get("vCPUs") or capabilities.get("vCPUS") or "99"
    try:
        return int(raw)
    except ValueError:
        return 99


def _sku_restricted_for_location(sku: Any) -> bool:
    for restriction in sku.restrictions or []:
        rtype = (getattr(restriction, "type", None) or "").lower()
        reason = (getattr(restriction, "reason_code", None) or "").lower()
        if rtype == "location" and reason in (
            "notavailableforsubscription",
            "quotaid",
        ):
            return True
    return False


def _sku_architecture(capabilities: dict[str, str]) -> str:
    return (capabilities.get("CpuArchitectureType") or "x64").lower()


def discover_azure_x64_vm_sizes(
    compute_client: Any,
    location: str,
    *,
    max_vcpus: int = MAX_VCPUS_DEFAULT,
) -> list[str]:
    """List x64 VM SKUs Azure reports as available in this region for the subscription."""
    loc = (location or "").strip().lower()
    if not loc:
        return []

    found: list[str] = []
    try:
        for sku in compute_client.resource_skus.list(filter=f"location eq '{loc}'"):
            if (getattr(sku, "resource_type", None) or "").lower() != "virtualmachines":
                continue
            name = getattr(sku, "name", None) or ""
            if not name.startswith("Standard_"):
                continue
            if _likely_arm_sku(name):
                continue
            caps = {
                (c.name or ""): (c.value or "")
                for c in (getattr(sku, "capabilities", None) or [])
            }
            if "arm" in _sku_architecture(caps):
                continue
            if _sku_vcpus(caps) > max_vcpus:
                continue
            if _sku_restricted_for_location(sku):
                continue
            found.append(name)
    except Exception:
        return []

    return _rank_vm_sizes(found)


def _rank_vm_sizes(names: list[str]) -> list[str]:
    priority = {name: idx for idx, name in enumerate(AZURE_VM_SIZE_PRIORITY)}

    def sort_key(name: str) -> tuple[int, str]:
        return (priority.get(name, 100), name)

    return sorted(set(names), key=sort_key)


def azure_vm_sizes_for_deploy(
    compute_client: Any,
    location: str,
    primary: str,
    *,
    max_to_try: int = MAX_SIZES_TO_TRY,
) -> list[str]:
    """Wizard preference + static fallbacks + live region inventory."""
    merged: list[str] = []
    seen: set[str] = set()
    for size in azure_vm_sizes_to_try(primary):
        if size not in seen:
            seen.add(size)
            merged.append(size)
    for size in discover_azure_x64_vm_sizes(compute_client, location):
        if size not in seen:
            seen.add(size)
            merged.append(size)
    return merged[:max_to_try]


def format_no_vm_capacity_error(location: str, tried: list[str]) -> str:
    preview = ", ".join(tried[:12])
    extra = f" (+{len(tried) - 12} more)" if len(tried) > 12 else ""
    return (
        f"No VM sizes with capacity in {location} "
        f"(tried {len(tried)} x64 sizes: {preview}{extra}). "
        "Try westus2, eastus2, southcentralus, or westus3 in the wizard, "
        "or retry later — free/student subscriptions often have tight regional capacity."
    )
