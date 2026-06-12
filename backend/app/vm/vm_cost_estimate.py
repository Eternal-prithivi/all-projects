"""
Approximate VM slot cost overview for pre-provision UI.

Uses on-demand list pricing heuristics (US regions). Not a billing quote.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.cloud.providers import normalize_provider
from app.vm.cluster_catalog import (
    ProvisionSpec,
    cluster_create_spec,
    cluster_vms,
    find_slot_by_vm_name,
    get_cluster_definition,
    infer_cluster_from_vm_name,
)
from app.vm.models import ClusterType

HOURS_PER_MONTH = 730
CURRENCY = "USD"

DISCLAIMER = (
    "Approximate on-demand pricing for one VM in a typical US region. "
    "Actual charges vary by region, discounts, egress, and runtime. "
    "Not a billing invoice."
)

EPHEMERAL_NOTE = (
    "Zenith VMs are ephemeral — you are charged only while an instance is running. "
    "Release the VM when finished to stop compute charges."
)

# Approximate monthly on-demand compute (USD) — fallback uses tier heuristics.
_AWS_COMPUTE_MONTHLY: Dict[str, float] = {
    "t3.micro": 7.59,
    "t3.small": 15.18,
    "t3.medium": 30.37,
    "t3.large": 60.74,
    "m5.large": 70.08,
    "m5.xlarge": 140.16,
    "m5.2xlarge": 280.32,
    "m5d.2xlarge": 302.40,
    "m5n.large": 78.84,
    "m5n.xlarge": 157.68,
    "r5.large": 91.98,
    "r5.xlarge": 183.96,
    "r5.2xlarge": 367.92,
    "c5.xlarge": 122.40,
    "g4dn.xlarge": 384.00,
}

_GCP_COMPUTE_MONTHLY: Dict[str, float] = {
    "e2-micro": 5.11,
    "e2-small": 12.23,
    "e2-medium": 24.46,
    "e2-standard-2": 48.92,
    "e2-standard-4": 97.84,
    "e2-standard-8": 195.68,
    "n2-standard-2": 67.15,
    "n2-standard-4": 134.30,
    "n2-standard-8": 268.60,
    "n2-standard-16": 537.20,
    "n2-highmem-2": 90.94,
    "n2-highmem-4": 181.88,
    "n2-highmem-8": 363.76,
    "c2-standard-4": 145.00,
    "n1-standard-4": 140.00,
}

_AZURE_COMPUTE_MONTHLY: Dict[str, float] = {
    "Standard_B1s": 7.59,
    "Standard_B2s": 30.37,
    "Standard_D2s_v3": 70.08,
    "Standard_D4s_v3": 140.16,
    "Standard_D8s_v3": 280.32,
    "Standard_E4s_v3": 201.60,
    "Standard_E8s_v3": 403.20,
    "Standard_E16s_v3": 806.40,
    "Standard_F4s_v2": 120.00,
    "Standard_NC4as_T4_v3": 450.00,
}

_DISK_GB_MONTHLY_RATE: Dict[str, float] = {
    "": 0.08,
    "gp3": 0.08,
    "pd-standard": 0.04,
    "pd-balanced": 0.10,
    "Standard_LRS": 0.05,
    "pd-ssd": 0.17,
    "io2": 0.125,
    "Premium_LRS": 0.15,
}


def _compute_monthly(csp: str, machine_type: str) -> float:
    provider = normalize_provider(csp)
    table = (
        _AWS_COMPUTE_MONTHLY
        if provider == "AWS"
        else _AZURE_COMPUTE_MONTHLY
        if provider == "Azure"
        else _GCP_COMPUTE_MONTHLY
    )
    if machine_type in table:
        return table[machine_type]
    # Heuristic: scale unknown types by vCPU hint in name
    if "micro" in machine_type or "B1" in machine_type:
        return 7.0
    if "small" in machine_type or "2xlarge" not in machine_type and "xlarge" not in machine_type:
        if "large" in machine_type or "standard-4" in machine_type or "D4" in machine_type:
            return 95.0
        if "medium" in machine_type or "standard-2" in machine_type:
            return 45.0
        return 20.0
    if "2xlarge" in machine_type or "standard-16" in machine_type or "E16" in machine_type:
        return 380.0
    if "xlarge" in machine_type or "standard-8" in machine_type or "D8" in machine_type:
        return 190.0
    if "highmem" in machine_type or machine_type.startswith("r5"):
        return 120.0
    if "g4dn" in machine_type or "NC4" in machine_type:
        return 380.0
    return 60.0


def _disk_monthly(spec: ProvisionSpec) -> float:
    rate = _DISK_GB_MONTHLY_RATE.get(spec.disk_type or "", 0.08)
    cost = spec.disk_gb * rate
    if spec.disk_iops and (spec.disk_type or "") in ("io2", "gp3"):
        cost += spec.disk_iops * 0.005
    return round(cost, 2)


def _usage_examples(hourly: float) -> List[Dict[str, Any]]:
    scenarios = [
        ("always_on", "24/7 for a month", HOURS_PER_MONTH),
        ("business_hours", "~8h/day, weekdays", 176),
        ("light", "~40 hours / month", 40),
    ]
    out: List[Dict[str, Any]] = []
    for key, label, hours in scenarios:
        total = round(hourly * hours, 2)
        out.append(
            {
                "id": key,
                "label": label,
                "hours": hours,
                "estimated_usd": total,
            }
        )
    return out


def _line_items(spec: ProvisionSpec, compute: float, disk: float) -> List[Dict[str, Any]]:
    items = [
        {
            "name": f"Compute ({spec.machine_type})",
            "monthly_usd": round(compute, 2),
            "note": "On-demand instance, approximate.",
        },
        {
            "name": f"Boot disk ({spec.disk_gb} GB)",
            "monthly_usd": disk,
            "note": (
                f"{spec.disk_type} class"
                if spec.disk_type
                else "Standard block storage"
            ),
        },
    ]
    if spec.disk_iops:
        items.append(
            {
                "name": "Provisioned IOPS (disk)",
                "monthly_usd": round(spec.disk_iops * 0.005, 2),
                "note": "Included in disk line when applicable.",
            }
        )
    return items


def estimate_from_provision_spec(
    csp: str,
    spec: ProvisionSpec,
    *,
    cluster_type: str,
    tier_label: str = "",
    vm_name: Optional[str] = None,
) -> Dict[str, Any]:
    compute = _compute_monthly(csp, spec.machine_type)
    disk = _disk_monthly(spec)
    total = round(compute + disk, 2)
    hourly = round(total / HOURS_PER_MONTH, 4)

    return {
        "csp": normalize_provider(csp),
        "vm_name": vm_name,
        "cluster_type": cluster_type,
        "tier_label": tier_label,
        "machine_type": spec.machine_type,
        "disk_gb": spec.disk_gb,
        "disk_type": spec.disk_type or None,
        "currency": CURRENCY,
        "is_approximate": True,
        "disclaimer": DISCLAIMER,
        "ephemeral_note": EPHEMERAL_NOTE,
        "compute_monthly_usd": round(compute, 2),
        "disk_monthly_usd": disk,
        "total_monthly_usd": total,
        "hourly_usd": hourly,
        "line_items": _line_items(spec, compute, disk),
        "usage_examples": _usage_examples(hourly),
    }


def estimate_vm_slot_cost(
    csp: str,
    *,
    vm_name: Optional[str] = None,
    cluster_type: Optional[ClusterType] = None,
) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    ct = cluster_type
    if vm_name and ct is None:
        ct = infer_cluster_from_vm_name(vm_name)
    if ct is None:
        ct = ClusterType.GENERAL
    if vm_name:
        spec = cluster_create_spec(provider, ct, vm_name)
        slot = find_slot_by_vm_name(vm_name, provider)
        tier_label = slot.tier_label if slot else ""
        return estimate_from_provision_spec(
            provider,
            spec,
            cluster_type=ct.value,
            tier_label=tier_label,
            vm_name=vm_name,
        )

    # Default to first slot in cluster when no VM name provided
    first_slot = cluster_vms(provider, ct)[0]
    return estimate_vm_slot_cost(provider, vm_name=first_slot, cluster_type=ct)


def estimate_cluster_cost_range(csp: str, cluster_type: ClusterType) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    estimates = [
        estimate_vm_slot_cost(provider, vm_name=name, cluster_type=cluster_type)
        for name in cluster_vms(provider, cluster_type)
    ]
    totals = [e["total_monthly_usd"] for e in estimates]
    hourlies = [e["hourly_usd"] for e in estimates]
    return {
        "csp": provider,
        "cluster_type": cluster_type.value,
        "currency": CURRENCY,
        "is_approximate": True,
        "disclaimer": DISCLAIMER,
        "ephemeral_note": EPHEMERAL_NOTE,
        "min_monthly_usd": min(totals),
        "max_monthly_usd": max(totals),
        "min_hourly_usd": min(hourlies),
        "max_hourly_usd": max(hourlies),
        "slots": estimates,
    }
