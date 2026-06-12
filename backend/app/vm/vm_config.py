"""Unified VM configuration for topology click and config modal."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.cloud.providers import normalize_provider
from app.database.mongo_client import get_database
from app.vm.cluster_catalog import (
    find_slot_by_vm_name,
    get_cluster_definition,
    infer_cluster_from_vm_name,
    resolve_vm_alias,
)
from app.vm import vm_provider
from app.vm.vm_cost_estimate import estimate_vm_slot_cost
from app.vm.models import ClusterType

DB = get_database()

_MACHINE_SPECS: Dict[str, Dict[str, float]] = {
    "e2-micro": {"cpus": 2, "memory_gb": 1},
    "e2-small": {"cpus": 2, "memory_gb": 2},
    "e2-medium": {"cpus": 2, "memory_gb": 4},
    "e2-standard-2": {"cpus": 2, "memory_gb": 8},
    "e2-standard-4": {"cpus": 4, "memory_gb": 16},
    "e2-standard-8": {"cpus": 8, "memory_gb": 32},
    "n2-highmem-2": {"cpus": 2, "memory_gb": 16},
    "n2-highmem-4": {"cpus": 4, "memory_gb": 32},
    "n2-highmem-8": {"cpus": 8, "memory_gb": 64},
    "n2-standard-2": {"cpus": 2, "memory_gb": 8},
    "n2-standard-4": {"cpus": 4, "memory_gb": 16},
    "n2-standard-8": {"cpus": 8, "memory_gb": 32},
    "n2-standard-16": {"cpus": 16, "memory_gb": 64},
    "m5.2xlarge": {"cpus": 8, "memory_gb": 32},
    "m5d.2xlarge": {"cpus": 8, "memory_gb": 32},
    "m5n.xlarge": {"cpus": 4, "memory_gb": 16},
    "m5n.large": {"cpus": 2, "memory_gb": 8},
    "r5.large": {"cpus": 2, "memory_gb": 16},
    "r5.xlarge": {"cpus": 4, "memory_gb": 32},
    "r5.2xlarge": {"cpus": 8, "memory_gb": 64},
    "t3.micro": {"cpus": 2, "memory_gb": 1},
    "t3.small": {"cpus": 2, "memory_gb": 2},
    "t3.medium": {"cpus": 2, "memory_gb": 4},
    "t3.large": {"cpus": 2, "memory_gb": 8},
    "m5.large": {"cpus": 2, "memory_gb": 8},
    "m5.xlarge": {"cpus": 4, "memory_gb": 16},
    "Standard_B1s": {"cpus": 1, "memory_gb": 1},
    "Standard_B2s": {"cpus": 2, "memory_gb": 4},
    "Standard_D2s_v3": {"cpus": 2, "memory_gb": 8},
    "Standard_D4s_v3": {"cpus": 4, "memory_gb": 16},
    "Standard_D8s_v3": {"cpus": 8, "memory_gb": 32},
    "Standard_E4s_v3": {"cpus": 4, "memory_gb": 32},
    "Standard_E8s_v3": {"cpus": 8, "memory_gb": 64},
    "Standard_E16s_v3": {"cpus": 16, "memory_gb": 128},
}


def _specs_for_machine(machine_type: str) -> Dict[str, float]:
    base = machine_type.split("/")[-1] if machine_type else ""
    return _MACHINE_SPECS.get(base, {"cpus": 2, "memory_gb": 4})


def build_vm_configuration(
    vm_name: str,
    csp: str,
    *,
    platform_region_slug: Optional[str] = None,
) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    canonical = resolve_vm_alias(vm_name, provider)
    cluster_type = infer_cluster_from_vm_name(canonical)
    definition = get_cluster_definition(cluster_type)
    slot = find_slot_by_vm_name(canonical, provider)
    zone = vm_provider.vm_zone(provider)

    active_users = DB["vm_assignments"].count_documents({
        "vm_name": {"$in": [vm_name, canonical]},
        "status": "active",
    })

    latest_metrics = DB["vm_metrics"].find_one(
        {"vm_name": {"$in": [vm_name, canonical]}},
        sort=[("collected_at", -1)],
    )

    intended = slot.spec_for(provider) if slot else None
    details = vm_provider.get_vm_details(provider, canonical, zone)
    status = details.get("status", "NOT_PROVISIONED")
    machine_type = details.get("machine_type") or (
        intended.machine_type if intended else "unknown"
    )
    specs = _specs_for_machine(machine_type)

    disks = []
    if status not in ("NOT_PROVISIONED", "UNKNOWN"):
        disks.append(
            {
                "name": "boot",
                "size_gb": intended.disk_gb if intended else 30,
                "type": "PERSISTENT",
                "boot": True,
            }
        )
    elif intended:
        disk_label = intended.disk_type or "PERSISTENT"
        disks.append(
            {
                "name": "boot",
                "size_gb": intended.disk_gb,
                "type": disk_label,
                "boot": True,
            }
        )

    external_ip = details.get("external_ip", "N/A")
    networks = [
        {
            "network": "default",
            "internal_ip": details.get("internal_ip", "N/A"),
            "external_ip": external_ip if external_ip != "N/A" else None,
        }
    ]

    cost_estimate = None
    if intended:
        cost_estimate = estimate_vm_slot_cost(
            provider,
            vm_name=canonical,
            cluster_type=cluster_type,
        )

    return {
        "vm_name": canonical,
        "display_name": (
            f"{definition.label} · {slot.tier_label}"
            if slot
            else canonical
        ),
        "status": status,
        "cluster_type": cluster_type.value.upper(),
        "tier": slot.tier if slot else None,
        "tier_label": slot.tier_label if slot else None,
        "slot_index": slot.slot_index if slot else None,
        "csp": provider,
        "region": zone,
        "machine_type": machine_type,
        "cpu_cores": specs["cpus"],
        "memory_gb": specs["memory_gb"],
        "disks": disks,
        "total_disk_gb": sum(d.get("size_gb", 0) for d in disks),
        "networks": networks,
        "zone": zone,
        "created": details.get("creation_timestamp"),
        "active_users": active_users,
        "intended_spec": intended.to_dict() if intended else None,
        "labels": details.get("labels", {}),
        "current_metrics": {
            "cpu_usage": latest_metrics.get("cpu_usage", 0) if latest_metrics else 0,
            "memory_usage": latest_metrics.get("memory_usage", 0) if latest_metrics else 0,
            "disk_usage_gb": latest_metrics.get("disk_usage_gb", 0) if latest_metrics else 0,
            "network_in_mb": latest_metrics.get("network_in_mb", 0) if latest_metrics else 0,
            "network_out_mb": latest_metrics.get("network_out_mb", 0) if latest_metrics else 0,
        }
        if latest_metrics
        else None,
        "catalog_description": definition.description,
        "cost_estimate": cost_estimate,
    }
