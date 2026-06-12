"""GCP Compute Engine SDK module."""

from __future__ import annotations

import time
from typing import Any

from google.api_core import exceptions as gcp_exc
from google.cloud import compute_v1

from app.provision.provision_config_options import (
    gce_source_image,
    normalize_gce_os,
    normalize_gce_startup_script,
)
from app.provision.sdk_clients import gcp_compute_clients
from app.provision.sdk_modules.common import disk_gb, gcp_labels, gcp_zone
from app.provision.sdk_modules.context import SdkDeployContext

VPC_NAME = "zenith-vpc"
SUBNET_NAME = "zenith-subnet"


def plan_gce(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    name = config.get("instance_name") or "main-instance"
    machine = config.get("machine_type") or "e2-micro"
    os_key = normalize_gce_os(config.get("gce_os"))
    lines = [f"  + google_compute_instance.{name} ({machine}, {os_key})"]
    if (config.get("gce_startup_script") or "").strip():
        lines.append("  + metadata.startup-script")
    if config.get("enable_gcp_service_account"):
        lines.append("  + service_account attachment at launch")
    return {"lines": lines, "error": None, "resources": [f"gce:{name}"]}


def apply_gce(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    if not ctx.gcp_subnet_name and not ctx.gcp_network_name:
        return {"success": False, "steps": [], "error": "GCE requires VPC network (enable gcp_network)."}
    _, _, instances, project = gcp_compute_clients(cloud_env)
    region = config.get("gcp_region") or "us-central1"
    zone = ctx.gce_zone or gcp_zone(region)
    name = (config.get("instance_name") or "main-instance").strip() or "main-instance"
    machine = config.get("machine_type") or "e2-micro"
    disk = disk_gb(config)
    net = ctx.gcp_network_name or VPC_NAME
    subnet = ctx.gcp_subnet_name or SUBNET_NAME
    source_image = gce_source_image(config.get("gce_os"))
    startup_script = normalize_gce_startup_script(
        config.get("gce_startup_script"),
        config.get("gce_os"),
    )
    steps: list[str] = []
    try:
        try:
            instances.get(project=project, zone=zone, instance=name)
            steps.append(f"✓ GCE instance '{name}' already exists")
        except gcp_exc.NotFound:
            instance_kwargs: dict[str, Any] = {
                "name": name,
                "machine_type": f"zones/{zone}/machineTypes/{machine}",
                "disks": [
                    compute_v1.AttachedDisk(
                        boot=True,
                        auto_delete=True,
                        initialize_params=compute_v1.AttachedDiskInitializeParams(
                            source_image=source_image,
                            disk_size_gb=disk,
                        ),
                    )
                ],
                "network_interfaces": [
                    compute_v1.NetworkInterface(
                        subnetwork=f"projects/{project}/regions/{region}/subnetworks/{subnet}",
                        access_configs=[
                            compute_v1.AccessConfig(name="External NAT", type_="ONE_TO_ONE_NAT")
                        ],
                    )
                ],
                "labels": gcp_labels(config.get("tags")),
            }
            if startup_script:
                instance_kwargs["metadata"] = compute_v1.Metadata(
                    items=[compute_v1.Items(key="startup-script", value=startup_script)]
                )
            sa_email = (ctx.service_account_email or "").strip()
            if config.get("enable_gcp_service_account") and sa_email:
                instance_kwargs["service_accounts"] = [
                    compute_v1.ServiceAccount(
                        email=sa_email,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                ]
            instance = compute_v1.Instance(**instance_kwargs)
            op = instances.insert(project=project, zone=zone, instance_resource=instance)
            op.result()
            boot_note = f", {normalize_gce_os(config.get('gce_os'))}"
            steps.append(f"✓ GCE instance '{name}' ({machine}, {disk}GB{boot_note})")
            if startup_script:
                steps.append("✓ Startup script attached (metadata)")
            if sa_email:
                steps.append(f"✓ Service account attached ({sa_email})")
        ctx.gce_name = name
        ctx.gce_zone = zone
        ctx.gcp_project = project
        for _ in range(20):
            inst = instances.get(project=project, zone=zone, instance=name)
            for nic in inst.network_interfaces or []:
                if nic.access_configs and nic.access_configs[0].nat_i_p:
                    ctx.public_ip = nic.access_configs[0].nat_i_p
                    break
            if ctx.public_ip:
                break
            time.sleep(3)
        ip_note = f" ({ctx.public_ip})" if ctx.public_ip else ""
        if steps and ip_note:
            steps[-1] = steps[-1] + ip_note
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_gce(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    _, _, instances, project = gcp_compute_clients(cloud_env)
    zone = ctx.gce_zone or gcp_zone(config.get("gcp_region") or "us-central1")
    name = ctx.gce_name or config.get("instance_name") or "main-instance"
    steps: list[str] = []
    try:
        try:
            instances.delete(project=project, zone=zone, instance=name).result()
            steps.append(f"✓ Deleted GCE instance '{name}'")
        except gcp_exc.NotFound:
            pass
        return {"success": True, "steps": steps or ["GCE: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_gce_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    _, _, instances, project = gcp_compute_clients(cloud_env)
    zone = ctx.gce_zone or gcp_zone(config.get("gcp_region") or "us-central1")
    name = ctx.gce_name or config.get("instance_name") or "main-instance"
    try:
        instances.get(project=project, zone=zone, instance=name)
        return 0, []
    except gcp_exc.NotFound:
        return 1, [f"~ GCE instance '{name}' missing"]
    except Exception as exc:
        return 1, [f"~ GCE check failed: {exc}"]
