"""Azure VM attached resource cleanup — NIC, public IP, and managed OS/data disks."""

from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Set, Tuple

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def os_disk_name(vm_name: str) -> str:
    return f"{vm_name}-osdisk"


def nic_resource_name(vm_name: str) -> str:
    return f"{vm_name}-nic"


def public_ip_resource_name(vm_name: str) -> str:
    return f"{vm_name}-pip"


def os_disk_profile(disk_size_gb: int, storage_type: str, vm_name: str) -> dict[str, Any]:
    """OS disk spec with explicit name and auto-delete when the VM is removed."""
    return {
        "name": os_disk_name(vm_name),
        "create_option": "FromImage",
        "delete_option": "Delete",
        "disk_size_gb": disk_size_gb,
        "managed_disk": {"storage_account_type": storage_type},
    }


def collect_managed_disk_ids(vm: Any) -> List[str]:
    """ARM resource IDs for OS and data managed disks attached to a VM."""
    if not vm:
        return []
    ids: List[str] = []
    profile = getattr(vm, "storage_profile", None)
    if not profile:
        return ids

    os_disk = getattr(profile, "os_disk", None)
    managed = getattr(os_disk, "managed_disk", None) if os_disk else None
    if managed and getattr(managed, "id", None):
        ids.append(managed.id)

    for data_disk in getattr(profile, "data_disks", None) or []:
        managed = getattr(data_disk, "managed_disk", None)
        if managed and getattr(managed, "id", None):
            ids.append(managed.id)
    return ids


def _parse_disk_arm_id(disk_id: str) -> Optional[Tuple[str, str]]:
    parts = (disk_id or "").split("/")
    try:
        rg_idx = parts.index("resourceGroups")
        disk_idx = parts.index("disks")
        return parts[rg_idx + 1], parts[disk_idx + 1]
    except ValueError:
        return None


def _is_not_found(exc: Exception) -> bool:
    if exc.__class__.__name__ == "ResourceNotFoundError":
        return True
    message = str(exc).lower()
    return "not found" in message or "resourcenotfound" in message


def _delete_named_resource(
    label: str,
    deleter: Callable,
    rg: str,
    name: str,
) -> bool:
    if not name:
        return False
    try:
        deleter(rg, name).result()
        logger.info("Deleted Azure %s '%s' in %s", label, name, rg)
        return True
    except Exception as exc:
        if _is_not_found(exc):
            return False
        logger.warning("Failed to delete Azure %s '%s' in %s: %s", label, name, rg, exc)
        return False


def disks_linked_to_vm(compute_client, rg: str, vm_name: str) -> List[str]:
    """Managed disk names in the RG that match Zenith/Azure naming for this VM."""
    names: List[str] = []
    expected_os = os_disk_name(vm_name)
    for disk in compute_client.disks.list_by_resource_group(rg):
        dname = disk.name or ""
        if dname == expected_os:
            names.append(dname)
            continue
        if dname.startswith(f"{vm_name}_") or dname.startswith(f"{vm_name}-"):
            names.append(dname)
    return names


def cleanup_vm_attached_resources(
    compute_client,
    network_client,
    rg: str,
    vm_name: str,
    *,
    vm: Any = None,
    extra_disk_ids: Optional[Iterable[str]] = None,
    delete_vm_if_present: bool = False,
) -> dict[str, bool]:
    """
    Remove NIC, public IP, and managed disks for a VM slot.

    Call after VM deletion, or with delete_vm_if_present=True to roll back a failed create.
    """
    result = {
        "vm_deleted": False,
        "nic_deleted": False,
        "pip_deleted": False,
        "disks_deleted": False,
    }

    if delete_vm_if_present:
        try:
            compute_client.virtual_machines.get(rg, vm_name)
        except Exception as exc:
            if not _is_not_found(exc):
                logger.warning("Azure VM lookup failed for '%s': %s", vm_name, exc)
        else:
            try:
                compute_client.virtual_machines.begin_delete(
                    rg,
                    vm_name,
                    force_deletion=True,
                ).result()
                result["vm_deleted"] = True
                logger.info("Deleted Azure VM '%s' in %s (rollback)", vm_name, rg)
            except Exception as exc:
                if not _is_not_found(exc):
                    logger.warning("Failed to delete Azure VM '%s' in %s: %s", vm_name, rg, exc)

    result["nic_deleted"] = _delete_named_resource(
        "NIC",
        network_client.network_interfaces.begin_delete,
        rg,
        nic_resource_name(vm_name),
    )
    result["pip_deleted"] = _delete_named_resource(
        "public IP",
        network_client.public_ip_addresses.begin_delete,
        rg,
        public_ip_resource_name(vm_name),
    )

    disk_names: Set[str] = set(disks_linked_to_vm(compute_client, rg, vm_name))
    for disk_id in extra_disk_ids or []:
        if not disk_id:
            continue
        parsed = _parse_disk_arm_id(disk_id)
        if parsed and parsed[0] == rg:
            disk_names.add(parsed[1])

    deleted_any_disk = False
    for disk_name in sorted(disk_names):
        if _delete_named_resource(
            "managed disk",
            compute_client.disks.begin_delete,
            rg,
            disk_name,
        ):
            deleted_any_disk = True
    result["disks_deleted"] = deleted_any_disk
    return result
