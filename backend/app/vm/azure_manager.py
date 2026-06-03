"""Azure Compute VM lifecycle for Zenith cluster pools (parity with AWS/GCP)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.utils.logger import setup_logger
from app.vm.azure_runtime import (
    azure_location,
    azure_resource_group,
    azure_service_principal,
    azure_subscription_id,
)
from app.vm.models import ClusterType
from app.vm.ssh_manager import generate_ssh_keypair

logger = setup_logger(__name__)

ZENITH_TAG = "zenith_managed"
CLUSTER_TAG = "zenith_cluster"

AZURE_CLUSTER_VMS: dict[ClusterType, list[str]] = {
    ClusterType.GENERAL: ["general-azure-vm-1", "general-azure-vm-2"],
    ClusterType.STORAGE: ["storage-azure-vm-1", "storage-azure-vm-2"],
    ClusterType.MEMORY: ["memory-azure-vm-1", "memory-azure-vm-2"],
    ClusterType.PERFORMANCE: ["performance-azure-vm-1", "performance-azure-vm-2"],
    ClusterType.AI_ML: ["ai-ml-azure-vm-1", "ai-ml-azure-vm-2"],
}

_CLUSTER_SIZES: dict[str, str] = {
    "general": "Standard_B1s",
    "storage": "Standard_B2s",
    "memory": "Standard_B2s",
    "performance": "Standard_B2ms",
    "ai_ml": "Standard_B2ms",
}

_CLUSTER_DISK_GB: dict[str, int] = {
    "general": 8,
    "storage": 20,
    "memory": 16,
    "performance": 30,
    "ai_ml": 40,
}


def _clients():
    sp = azure_service_principal()
    if not all(sp.get(k) for k in ("tenant_id", "client_id", "client_secret", "subscription_id")):
        raise ValueError(
            "Azure VM requires subscription_id, tenant_id, client_id, and client_secret "
            "(BYOC service principal or platform .env)."
        )
    from azure.identity import ClientSecretCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.network import NetworkManagementClient

    credential = ClientSecretCredential(
        tenant_id=sp["tenant_id"],
        client_id=sp["client_id"],
        client_secret=sp["client_secret"],
    )
    sub = sp["subscription_id"]
    return (
        ComputeManagementClient(credential, sub),
        NetworkManagementClient(credential, sub),
    )


def _map_power_state(power_state: str) -> str:
    state = (power_state or "").lower()
    if "running" in state:
        return "RUNNING"
    if state in ("deallocated", "stopped", "stopping"):
        return "TERMINATED"
    if state in ("starting", "creating"):
        return "PROVISIONING"
    return state.upper() or "UNKNOWN"


def _vm_power_state(compute_client, rg: str, vm_name: str) -> str:
    view = compute_client.virtual_machines.instance_view(rg, vm_name)
    for status in view.statuses or []:
        code = status.code or ""
        if code.startswith("PowerState/"):
            return _map_power_state(code.split("/", 1)[-1])
    return "UNKNOWN"


def _public_ip(network_client, rg: str, vm) -> str:
    nics = vm.network_profile.network_interfaces if vm.network_profile else []
    if not nics:
        return "N/A"
    nic_id = nics[0].id
    if not nic_id:
        return "N/A"
    nic_name = nic_id.split("/")[-1]
    nic = network_client.network_interfaces.get(rg, nic_name)
    configs = nic.ip_configurations or []
    if not configs:
        return "N/A"
    pip_ref = configs[0].public_ip_address
    if not pip_ref or not pip_ref.id:
        return "N/A"
    pip_name = pip_ref.id.split("/")[-1]
    pip = network_client.public_ip_addresses.get(rg, pip_name)
    return pip.ip_address or "N/A"


def _tags_dict(vm) -> dict[str, str]:
    return dict(vm.tags or {})


def _get_subnet_id(network_client, rg: str) -> str:
    for vnet in network_client.virtual_networks.list(rg):
        for subnet in network_client.subnets.list(rg, vnet.name):
            return subnet.id
    raise ValueError(
        f"No subnet in resource group '{rg}'. "
        "Create a VNet/subnet or run Zenith Azure Terraform provision first."
    )


def _vm_by_name(compute_client, rg: str, name: str):
    try:
        return compute_client.virtual_machines.get(rg, name)
    except Exception:
        return None


def _nic_with_public_ip(network_client, rg: str, location: str, prefix: str):
    pip_name = f"{prefix}-pip"
    nic_name = f"{prefix}-nic"
    subnet_id = _get_subnet_id(network_client, rg)

    pip = network_client.public_ip_addresses.begin_create_or_update(
        rg,
        pip_name,
        {"location": location, "public_ip_allocation_method": "Dynamic"},
    ).result()

    nic = network_client.network_interfaces.begin_create_or_update(
        rg,
        nic_name,
        {
            "location": location,
            "ip_configurations": [
                {
                    "name": "ipconfig1",
                    "subnet": {"id": subnet_id},
                    "public_ip_address": {"id": pip.id},
                }
            ],
        },
    ).result()
    return nic


def list_vms() -> List[Dict[str, Any]]:
    if not azure_configured():
        return []
    try:
        compute_client, network_client = _clients()
        rg = azure_resource_group()
        location = azure_location()
        vms: list[dict[str, Any]] = []
        for vm in compute_client.virtual_machines.list(rg):
            tags = _tags_dict(vm)
            if tags.get(ZENITH_TAG) != "true":
                continue
            name = vm.name or "unknown"
            vms.append(
                {
                    "name": name,
                    "status": _vm_power_state(compute_client, rg, name),
                    "machine_type": (
                        vm.hardware_profile.vm_size
                        if vm.hardware_profile
                        else "unknown"
                    ),
                    "zone": location,
                    "labels": {
                        "cluster_type": tags.get(CLUSTER_TAG, "general"),
                        ZENITH_TAG: "true",
                    },
                    "creation_timestamp": None,
                    "network_interfaces": [
                        {
                            "network_ip": None,
                            "external_ip": _public_ip(network_client, rg, vm),
                        }
                    ],
                    "instance_id": vm.vm_id,
                }
            )
        return vms
    except Exception as exc:
        logger.error("Error listing Azure VMs: %s", exc)
        return []


def get_vm_details(name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    location = zone or azure_location()
    if not azure_configured():
        return {
            "name": name,
            "status": "UNKNOWN",
            "machine_type": "unknown",
            "zone": location,
            "external_ip": "N/A",
            "creation_timestamp": None,
            "labels": {},
        }
    compute_client, network_client = _clients()
    rg = azure_resource_group()
    vm = _vm_by_name(compute_client, rg, name)
    if not vm:
        return {
            "name": name,
            "status": "UNKNOWN",
            "machine_type": "unknown",
            "zone": location,
            "external_ip": "N/A",
            "creation_timestamp": None,
            "labels": {},
        }
    tags = _tags_dict(vm)
    return {
        "name": name,
        "status": _vm_power_state(compute_client, rg, name),
        "machine_type": (
            vm.hardware_profile.vm_size if vm.hardware_profile else "unknown"
        ),
        "zone": location,
        "external_ip": _public_ip(network_client, rg, vm),
        "creation_timestamp": None,
        "labels": {"cluster_type": tags.get(CLUSTER_TAG, "general")},
        "instance_id": vm.vm_id,
    }


def create_vm(
    name: str,
    machine_type: str,
    source_image: str = "",
    disk_size_gb: int = 8,
    labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    del source_image  # Azure uses publisher/offer/sku below
    compute_client, network_client = _clients()
    rg = azure_resource_group()
    location = azure_location()
    existing = _vm_by_name(compute_client, rg, name)
    if existing:
        return {
            "name": name,
            "status": _vm_power_state(compute_client, rg, name),
            "details": get_vm_details(name, location),
        }

    cluster = (labels or {}).get("cluster_type", "general")
    tags = {
        "Name": name,
        ZENITH_TAG: "true",
        CLUSTER_TAG: cluster,
    }
    for key, value in (labels or {}).items():
        if key not in tags:
            tags[key] = str(value)

    nic = _nic_with_public_ip(network_client, rg, location, name)
    _, public_key = generate_ssh_keypair()
    computer_name = name.replace("-", "")[:15] or "zenithvm"

    vm_params = {
        "location": location,
        "tags": tags,
        "hardware_profile": {"vm_size": machine_type},
        "storage_profile": {
            "image_reference": {
                "publisher": "Debian",
                "offer": "debian-11",
                "sku": "11",
                "version": "latest",
            },
            "os_disk": {
                "create_option": "FromImage",
                "disk_size_gb": disk_size_gb,
                "managed_disk": {"storage_account_type": "Standard_LRS"},
            },
        },
        "os_profile": {
            "computer_name": computer_name,
            "admin_username": "azureuser",
            "linux_configuration": {
                "disable_password_authentication": True,
                "ssh": {
                    "public_keys": [
                        {
                            "path": "/home/azureuser/.ssh/authorized_keys",
                            "key_data": public_key,
                        }
                    ]
                },
            },
        },
        "network_profile": {
            "network_interfaces": [{"id": nic.id, "properties": {"primary": True}}]
        },
    }

    logger.info(
        "Creating Azure VM '%s' size '%s' in %s/%s",
        name,
        machine_type,
        rg,
        location,
    )
    poller = compute_client.virtual_machines.begin_create_or_update(rg, name, vm_params)
    poller.result()
    details = get_vm_details(name, location)
    return {"name": name, "status": "RUNNING", "details": details}


def start_vm(name: str) -> Dict[str, Any]:
    compute_client, _network_client = _clients()
    rg = azure_resource_group()
    vm = _vm_by_name(compute_client, rg, name)
    if not vm:
        raise ValueError(f"Azure VM '{name}' not found")
    state = _vm_power_state(compute_client, rg, name)
    if state == "TERMINATED":
        compute_client.virtual_machines.begin_start(rg, name).result()
    details = get_vm_details(name, azure_location())
    return {"name": name, "status": "RUNNING", "details": details}


def stop_vm(name: str) -> Dict[str, Any]:
    compute_client, _network_client = _clients()
    rg = azure_resource_group()
    vm = _vm_by_name(compute_client, rg, name)
    if not vm:
        raise ValueError(f"Azure VM '{name}' not found")
    if _vm_power_state(compute_client, rg, name) == "RUNNING":
        compute_client.virtual_machines.begin_deallocate(rg, name).result()
    details = get_vm_details(name, azure_location())
    return {"name": name, "status": "TERMINATED", "details": details}


def delete_vm(name: str) -> Dict[str, Any]:
    compute_client, network_client = _clients()
    rg = azure_resource_group()
    vm = _vm_by_name(compute_client, rg, name)
    if not vm:
        return {"name": name, "status": "DELETED"}
    compute_client.virtual_machines.begin_delete(rg, name).result()
    for suffix in ("-nic", "-pip"):
        resource = f"{name}{suffix}"
        try:
            if suffix == "-nic":
                network_client.network_interfaces.begin_delete(rg, resource).result()
            else:
                network_client.public_ip_addresses.begin_delete(rg, resource).result()
        except Exception:
            pass
    return {"name": name, "status": "DELETED"}


def cluster_machine_type(cluster_type: ClusterType) -> str:
    return _CLUSTER_SIZES.get(cluster_type.value, "Standard_B1s")


def cluster_disk_gb(cluster_type: ClusterType) -> int:
    return _CLUSTER_DISK_GB.get(cluster_type.value, 8)


def azure_configured() -> bool:
    sp = azure_service_principal()
    return bool(
        sp.get("subscription_id")
        and sp.get("tenant_id")
        and sp.get("client_id")
        and sp.get("client_secret")
    )
