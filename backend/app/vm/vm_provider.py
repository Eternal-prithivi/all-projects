"""Dispatch VM operations to GCP, AWS, or Azure backends."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from app.cloud.providers import CloudProvider, normalize_provider
from app.vm import aws_manager, azure_manager, manager as gcp_manager
from app.vm.aws_runtime import aws_user_context
from app.vm.azure_runtime import azure_user_context
from app.vm.gcp_runtime import gcp_user_context
from app.vm.models import ClusterType


def cluster_vms(csp: str, cluster: ClusterType) -> list[str]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.AWS_CLUSTER_VMS[cluster]
    if provider == "Azure":
        return azure_manager.AZURE_CLUSTER_VMS[cluster]
    return gcp_manager.CLUSTER_VMS[cluster]


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
) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.create_vm(
            name, machine_type, source_image, disk_size_gb, labels
        )
    if provider == "Azure":
        return azure_manager.create_vm(
            name, machine_type, source_image, disk_size_gb, labels
        )
    return gcp_manager.create_vm(name, machine_type, source_image, disk_size_gb, labels)


def start_vm(csp: str, name: str) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.start_vm(name)
    if provider == "Azure":
        return azure_manager.start_vm(name)
    return gcp_manager.start_vm(name)


def stop_vm(csp: str, name: str) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.stop_vm(name)
    if provider == "Azure":
        return azure_manager.stop_vm(name)
    return gcp_manager.stop_vm(name)


def delete_vm(csp: str, name: str) -> Dict[str, Any]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        return aws_manager.delete_vm(name)
    if provider == "Azure":
        return azure_manager.delete_vm(name)
    return gcp_manager.delete_vm(name)


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


@contextmanager
def vm_runtime_context(username: str, csp: str) -> Iterator[CloudProvider]:
    provider = normalize_provider(csp)
    if provider == "AWS":
        with aws_user_context(username):
            yield provider
    elif provider == "Azure":
        with azure_user_context(username):
            yield provider
    else:
        with gcp_user_context(username):
            yield provider
