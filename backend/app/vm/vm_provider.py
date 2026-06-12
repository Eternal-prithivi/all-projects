"""Dispatch VM operations to GCP, AWS, or Azure backends."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from app.cloud.providers import CloudProvider, normalize_provider
from app.vm import aws_manager, azure_manager, manager as gcp_manager
from app.vm.aws_runtime import aws_user_context
from app.vm.azure_runtime import azure_user_context
from app.vm.gcp_runtime import gcp_user_context
from app.vm.platform_region_context import (
    reset_platform_region_slug,
    set_platform_region_slug,
)
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.vm.cluster_catalog import (
    ProvisionSpec,
    cluster_create_spec as catalog_create_spec,
    cluster_max_vms as catalog_max_vms,
    cluster_vms as catalog_cluster_vms,
    find_slot_by_vm_name,
    resolve_vm_alias,
)

from app.vm.models import ClusterType

logger = setup_logger(__name__)

_STOPPED_STATUSES = frozenset({"TERMINATED", "STOPPED"})
_MISSING_STATUSES = frozenset({"NOT_PROVISIONED", "UNKNOWN"})
_ACTIVE_STATUSES = frozenset({"RUNNING", "PROVISIONING", "STAGING"})


def cluster_vms(csp: str, cluster: ClusterType) -> list[str]:
    return catalog_cluster_vms(csp, cluster)


def vm_zone(csp: str) -> str:
    provider = normalize_provider(csp)
    if provider == "AWS":
        from app.vm.aws_runtime import aws_region

        return aws_region()
    if provider == "Azure":
        from app.vm.azure_runtime import azure_location

        return azure_location()
    from app.vm.gcp_runtime import gcp_zone

    return gcp_zone()


def list_vms(csp: str = "GCP") -> List[Dict[str, Any]]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.list_vms()
    if provider == "Azure":
        return azure_manager.list_vms()
    return gcp_manager.list_vms()


def create_vm(
    csp: str,
    name: str,
    machine_type: str,
    source_image: str,
    disk_size_gb: int,
    labels: Optional[Dict[str, str]] = None,
    *,
    disk_type: str = "",
    disk_iops: Optional[int] = None,
) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.create_vm(
            name,
            machine_type,
            source_image,
            disk_size_gb,
            labels,
            disk_type=disk_type,
            disk_iops=disk_iops,
        )
    if provider == "Azure":
        return azure_manager.create_vm(
            name,
            machine_type,
            source_image,
            disk_size_gb,
            labels,
            disk_type=disk_type,
        )
    return gcp_manager.create_vm(
        name,
        machine_type,
        source_image,
        disk_size_gb,
        labels,
        disk_type=disk_type,
    )


def start_vm(csp: str, name: str) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.start_vm(name)
    if provider == "Azure":
        return azure_manager.start_vm(name)
    return gcp_manager.start_vm(name)


def stop_vm(csp: str, name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.stop_vm(name)
    if provider == "Azure":
        return azure_manager.stop_vm(name)
    return gcp_manager.stop_vm(name, zone=zone)


def delete_vm(csp: str, name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.delete_vm(name)
    if provider == "Azure":
        return azure_manager.delete_vm(name)
    return gcp_manager.delete_vm(name, zone=zone)


def get_vm_details(csp: str, name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.get_vm_details(name, zone)
    if provider == "Azure":
        return azure_manager.get_vm_details(name, zone)
    return gcp_manager.get_vm_details(name, zone or vm_zone(csp))


def cloud_configured(csp: str) -> bool:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.aws_configured()
    if provider == "Azure":
        return azure_manager.azure_configured()
    return gcp_manager.credentials is not None


def cluster_max_vms(cluster_type: ClusterType) -> int:
    return catalog_max_vms(cluster_type)


def cluster_create_spec(
    csp: str,
    cluster_type: ClusterType,
    slot_id: Optional[str] = None,
) -> ProvisionSpec:
    """Return launch parameters for a pool slot."""
    return catalog_create_spec(csp, cluster_type, slot_id)


def count_active_cluster_instances(csp: str, cluster_type: ClusterType) -> int:
    """Running/provisioning VMs in this cluster pool."""
    pool = set(cluster_vms(csp, cluster_type))
    return sum(
        1
        for vm in list_vms(csp)
        if vm.get("name") in pool and vm.get("status") in _ACTIVE_STATUSES
    )


def _external_ip_from_result(result: Dict[str, Any]) -> str:
    details = result.get("details") or {}
    return details.get("external_ip") or "N/A"


def _ephemeral_mode() -> bool:
    return bool(getattr(settings, "VM_DELETE_ON_IDLE", True))


def ensure_vm_running(
    csp: str,
    cluster_type: ClusterType,
    vm_name: str,
) -> Dict[str, str]:
    """
    Ensure a pool VM exists and is running.

    Ephemeral mode (VM_DELETE_ON_IDLE): terminate stopped instances and create fresh.
    Legacy mode: start stopped instances before creating new ones.
    """
    vm_name = resolve_vm_alias(vm_name, csp)
    zone = vm_zone(csp)
    details = get_vm_details(csp, vm_name, zone)
    status = details.get("status", "UNKNOWN")

    if status == "RUNNING":
        return {"vm_name": vm_name, "vm_ip": details.get("external_ip", "N/A")}

    if status in _STOPPED_STATUSES:
        if _ephemeral_mode():
            logger.info(
                "Ephemeral mode: removing stopped VM %s on %s before recreate",
                vm_name,
                csp,
            )
            try:
                delete_vm(csp, vm_name)
            except Exception as exc:
                logger.warning("Could not delete stopped %s: %s", vm_name, exc)
        else:
            try:
                result = start_vm(csp, vm_name)
                return {"vm_name": vm_name, "vm_ip": _external_ip_from_result(result)}
            except Exception as exc:
                logger.warning(
                    "Could not start %s on %s (%s); provisioning instead",
                    vm_name,
                    csp,
                    exc,
                )

    active_count = count_active_cluster_instances(csp, cluster_type)
    max_vms = cluster_max_vms(cluster_type)
    if active_count >= max_vms:
        raise ValueError(
            f"Cluster '{cluster_type.value}' is at capacity ({max_vms} running instances). "
            "Wait for a VM to become available or release an assignment."
        )

    spec = cluster_create_spec(csp, cluster_type, slot_id=vm_name)
    labels = {"cluster_type": cluster_type.value}
    logger.info(
        "Provisioning missing VM %s for %s cluster on %s",
        vm_name,
        cluster_type.value,
        csp,
    )
    result = create_vm(
        csp,
        vm_name,
        spec.machine_type,
        spec.source_image,
        spec.disk_gb,
        labels,
        disk_type=spec.disk_type,
        disk_iops=spec.disk_iops,
    )
    return {"vm_name": vm_name, "vm_ip": _external_ip_from_result(result)}


def ensure_cluster_vm_for_assignment(
    csp: str,
    cluster_type: ClusterType,
    vm_loads: List[Dict[str, Any]],
    vm_preference: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pick the best VM in a cluster pool and ensure it is running.
    Honors vm_preference when set; otherwise least-loaded running, then provision.
    """
    pool = cluster_vms(csp, cluster_type)
    loads_by_name = {vm["vm_name"]: vm for vm in vm_loads}

    if vm_preference:
        vm_preference = resolve_vm_alias(vm_preference, csp)
        if vm_preference not in pool:
            raise ValueError(
                f"VM '{vm_preference}' is not in the {cluster_type.value} pool. "
                f"Choose one of: {', '.join(pool)}"
            )
        pick = loads_by_name.get(vm_preference) or {
            "vm_name": vm_preference,
            "status": "UNKNOWN",
            "active_users": 0,
            "vm_ip": "N/A",
        }
        if pick.get("status") == "RUNNING":
            return pick
        ensured = ensure_vm_running(csp, cluster_type, vm_preference)
        return {
            "vm_name": ensured["vm_name"],
            "vm_ip": ensured["vm_ip"],
            "active_users": pick.get("active_users", 0),
            "status": "RUNNING",
        }

    running = sorted(
        [vm for vm in vm_loads if vm.get("status") == "RUNNING"],
        key=lambda vm: vm.get("active_users", 0),
    )
    if running:
        return running[0]

    if not _ephemeral_mode():
        stopped = sorted(
            [vm for vm in vm_loads if vm.get("status") in _STOPPED_STATUSES],
            key=lambda vm: vm.get("active_users", 0),
        )
        if stopped:
            pick = stopped[0]
            ensured = ensure_vm_running(csp, cluster_type, pick["vm_name"])
            return {
                "vm_name": ensured["vm_name"],
                "vm_ip": ensured["vm_ip"],
                "active_users": pick.get("active_users", 0),
                "status": "RUNNING",
            }

    for name in pool:
        status = loads_by_name.get(name, {}).get("status")
        if status in _MISSING_STATUSES or name not in loads_by_name:
            active_users = loads_by_name.get(name, {}).get("active_users", 0)
            ensured = ensure_vm_running(csp, cluster_type, name)
            return {
                "vm_name": ensured["vm_name"],
                "vm_ip": ensured["vm_ip"],
                "active_users": active_users,
                "status": "RUNNING",
            }

    if pool:
        ensured = ensure_vm_running(csp, cluster_type, pool[0])
        return {
            "vm_name": ensured["vm_name"],
            "vm_ip": ensured["vm_ip"],
            "active_users": 0,
            "status": "RUNNING",
        }

    raise ValueError(f"No VM pool configured for cluster '{cluster_type.value}'")


@contextmanager
def vm_runtime_context(
    username: str,
    csp: str,
    platform_region_slug: Optional[str] = None,
) -> Iterator[CloudProvider]:
    provider = normalize_provider(csp)
    region_token = set_platform_region_slug(platform_region_slug)
    try:
        if provider == "AWS":
            with aws_user_context(username):
                yield provider
        elif provider == "Azure":
            with azure_user_context(username):
                yield provider
        else:
            with gcp_user_context(username):
                yield provider
    finally:
        reset_platform_region_slug(region_token)
