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
from app.provision.provision_config_options import (
    azure_image_reference,
    normalize_azure_os,
)
from app.vm.cluster_catalog import (
    cluster_create_spec,
    cluster_types,
    cluster_vms as catalog_cluster_vms,
)
from app.vm.models import ClusterType
from app.vm.ssh_manager import generate_ssh_keypair
from app.vm.azure_cleanup import (
    cleanup_vm_attached_resources,
    collect_managed_disk_ids,
    os_disk_profile,
)

logger = setup_logger(__name__)

ZENITH_TAG = "zenith_managed"
CLUSTER_TAG = "zenith_cluster"

AZURE_CLUSTER_VMS: dict[ClusterType, list[str]] = {
    ct: catalog_cluster_vms("Azure", ct) for ct in cluster_types()
}

# Burstable B-series SKUs are often capacity-blocked; try these next.
_SIZE_FALLBACKS: tuple[str, ...] = (
    "Standard_D2s_v3",
    "Standard_D2s_v5",
    "Standard_B2ms",
    "Standard_B1ms",
)

_AZURE_MIN_OS_DISK_GB = 30


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


def _location_key(location: str) -> str:
    return (location or "").lower().replace(" ", "")


def _subnet_in_location(network_client, rg: str, location: str) -> Optional[str]:
    """Return a subnet id in the target Azure region, if one exists."""
    target = _location_key(location)
    for vnet in network_client.virtual_networks.list(rg):
        if _location_key(vnet.location or "") != target:
            continue
        for subnet in network_client.subnets.list(rg, vnet.name):
            if subnet.id:
                return subnet.id
    return None


def _ensure_subnet_id(network_client, rg: str, location: str) -> str:
    """
    Resolve a subnet in the VM's target region.

    Many subscriptions block Basic SKU public IPs; we also auto-create a small
    VNet/subnet per region when the platform RG only has networking in one region.
    """
    existing = _subnet_in_location(network_client, rg, location)
    if existing:
        return existing

    loc_key = _location_key(location)
    vnet_name = f"zenith-vnet-{loc_key}"
    subnet_name = "zenith-subnet"
    logger.info(
        "Creating Azure VNet '%s' and subnet in %s (resource group %s)",
        vnet_name,
        location,
        rg,
    )
    network_client.virtual_networks.begin_create_or_update(
        rg,
        vnet_name,
        {
            "location": location,
            "address_space": {"address_prefixes": ["10.42.0.0/16"]},
        },
    ).result()
    subnet = network_client.subnets.begin_create_or_update(
        rg,
        vnet_name,
        subnet_name,
        {"address_prefix": "10.42.1.0/24"},
    ).result()
    if not subnet.id:
        raise ValueError(
            f"Failed to create subnet in {location}. "
            "Check Azure permissions for Microsoft.Network/virtualNetworks/write."
        )
    return subnet.id


def _vm_by_name(compute_client, rg: str, name: str):
    try:
        return compute_client.virtual_machines.get(rg, name)
    except Exception:
        return None


def _nic_with_public_ip(network_client, rg: str, location: str, prefix: str):
    pip_name = f"{prefix}-pip"
    nic_name = f"{prefix}-nic"
    subnet_id = _ensure_subnet_id(network_client, rg, location)

    # Basic SKU public IPs are blocked in many regions (quota 0); use Standard.
    pip = network_client.public_ip_addresses.begin_create_or_update(
        rg,
        pip_name,
        {
            "location": location,
            "sku": {"name": "Standard"},
            "public_ip_allocation_method": "Static",
        },
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
            "status": "NOT_PROVISIONED",
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
    *,
    disk_type: str = "",
) -> Dict[str, Any]:
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
    os_disk_gb = max(int(disk_size_gb), _AZURE_MIN_OS_DISK_GB)
    storage_type = disk_type or "Standard_LRS"

    image_ref = azure_image_reference(
        normalize_azure_os((source_image or "").strip() or "debian_12")
    )
    base_params = {
        "location": location,
        "tags": tags,
        "storage_profile": {
            "image_reference": image_ref,
            "os_disk": os_disk_profile(os_disk_gb, storage_type, name),
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

    last_exc: Optional[Exception] = None
    for size in _vm_sizes_to_try(machine_type):
        vm_params = {**base_params, "hardware_profile": {"vm_size": size}}
        logger.info(
            "Creating Azure VM '%s' size '%s' in %s/%s",
            name,
            size,
            rg,
            location,
        )
        try:
            poller = compute_client.virtual_machines.begin_create_or_update(
                rg, name, vm_params
            )
            poller.result()
            details = get_vm_details(name, location)
            return {"name": name, "status": "RUNNING", "details": details}
        except Exception as exc:
            last_exc = exc
            if _is_sku_unavailable(exc):
                logger.warning(
                    "Azure size %s unavailable in %s for %s; trying fallback",
                    size,
                    location,
                    name,
                )
                continue
            _rollback_vm_resources(compute_client, network_client, rg, name)
            raise _azure_error("create VM", exc) from exc

    _rollback_vm_resources(compute_client, network_client, rg, name)
    raise _azure_error("create VM", last_exc or RuntimeError("No VM size available"))


def _rollback_vm_resources(compute_client, network_client, rg: str, vm_name: str) -> None:
    cleanup_vm_attached_resources(
        compute_client,
        network_client,
        rg,
        vm_name,
        delete_vm_if_present=True,
    )


def delete_vm(name: str) -> Dict[str, Any]:
    compute_client, network_client = _clients()
    rg = azure_resource_group()
    vm = _vm_by_name(compute_client, rg, name)
    disk_ids = collect_managed_disk_ids(vm)
    if vm:
        logger.info("Deleting Azure VM '%s' in resource group %s", name, rg)
        compute_client.virtual_machines.begin_delete(
            rg,
            name,
            force_deletion=True,
        ).result()
    cleanup_vm_attached_resources(
        compute_client,
        network_client,
        rg,
        name,
        extra_disk_ids=disk_ids,
    )
    return {"name": name, "status": "DELETED"}


def _azure_error(action: str, exc: Exception) -> ValueError:
    message = getattr(exc, "message", None) or str(exc)
    return ValueError(f"Azure failed to {action}: {message}")


def _is_sku_unavailable(exc: Exception) -> bool:
    code = getattr(exc, "error", None)
    if code is not None:
        inner = getattr(code, "code", None) or (code if isinstance(code, str) else "")
        if str(inner) == "SkuNotAvailable":
            return True
    return "SkuNotAvailable" in str(exc)


def _vm_sizes_to_try(machine_type: str) -> List[str]:
    sizes: List[str] = []
    for candidate in (machine_type, *_SIZE_FALLBACKS):
        if candidate and candidate not in sizes:
            sizes.append(candidate)
    return sizes


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


def cluster_machine_type(cluster_type: ClusterType, slot_id: Optional[str] = None) -> str:
    return cluster_create_spec("Azure", cluster_type, slot_id).machine_type


def cluster_disk_gb(cluster_type: ClusterType, slot_id: Optional[str] = None) -> int:
    return cluster_create_spec("Azure", cluster_type, slot_id).disk_gb


def azure_configured() -> bool:
    sp = azure_service_principal()
    return bool(
        sp.get("subscription_id")
        and sp.get("tenant_id")
        and sp.get("client_id")
        and sp.get("client_secret")
    )
