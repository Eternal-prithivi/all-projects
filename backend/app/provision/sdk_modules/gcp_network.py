"""GCP VPC network + subnet SDK module."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exc
from google.cloud import compute_v1

from app.provision.sdk_clients import gcp_compute_clients
from app.provision.sdk_modules.common import gcp_zone
from app.provision.sdk_modules.context import SdkDeployContext

VPC_NAME = "zenith-vpc"
SUBNET_NAME = "zenith-subnet"


def plan_gcp_network(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    region = config.get("gcp_region") or "us-central1"
    lines = [
        f"  + google_compute_network.{VPC_NAME}",
        f"  + google_compute_subnetwork.{SUBNET_NAME} ({region})",
    ]
    return {"lines": lines, "error": None, "resources": lines}


def apply_gcp_network(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    networks, subnetworks, _, project = gcp_compute_clients(cloud_env)
    region = config.get("gcp_region") or "us-central1"
    steps: list[str] = []
    try:
        try:
            networks.get(project=project, network=VPC_NAME)
        except gcp_exc.NotFound:
            op = networks.insert(
                project=project,
                network_resource=compute_v1.Network(
                    name=VPC_NAME,
                    auto_create_subnetworks=False,
                ),
            )
            op.result()
        steps.append(f"✓ VPC network '{VPC_NAME}'")
        ctx.gcp_network_name = VPC_NAME

        subnet_path = f"projects/{project}/regions/{region}/subnetworks/{SUBNET_NAME}"
        try:
            subnetworks.get(project=project, region=region, subnetwork=SUBNET_NAME)
        except gcp_exc.NotFound:
            op = subnetworks.insert(
                project=project,
                region=region,
                subnetwork_resource=compute_v1.Subnetwork(
                    name=SUBNET_NAME,
                    network=f"projects/{project}/global/networks/{VPC_NAME}",
                    ip_cidr_range="10.0.1.0/24",
                    region=region,
                ),
            )
            op.result()
        steps.append(f"✓ Subnet '{SUBNET_NAME}'")
        ctx.gcp_subnet_name = SUBNET_NAME
        ctx.gcp_project = project
        ctx.gce_zone = gcp_zone(region)
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_gcp_network(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    networks, subnetworks, _, project = gcp_compute_clients(cloud_env)
    region = config.get("gcp_region") or "us-central1"
    steps: list[str] = []
    try:
        subnet = ctx.gcp_subnet_name or SUBNET_NAME
        try:
            subnetworks.delete(project=project, region=region, subnetwork=subnet).result()
            steps.append(f"✓ Deleted subnet '{subnet}'")
        except gcp_exc.NotFound:
            pass
        net = ctx.gcp_network_name or VPC_NAME
        try:
            networks.delete(project=project, network=net).result()
            steps.append(f"✓ Deleted network '{net}'")
        except gcp_exc.NotFound:
            pass
        return {"success": True, "steps": steps or ["GCP network: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_gcp_network_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    networks, subnetworks, _, project = gcp_compute_clients(cloud_env)
    region = config.get("gcp_region") or "us-central1"
    try:
        networks.get(project=project, network=ctx.gcp_network_name or VPC_NAME)
        subnetworks.get(
            project=project,
            region=region,
            subnetwork=ctx.gcp_subnet_name or SUBNET_NAME,
        )
        return 0, []
    except gcp_exc.NotFound:
        return 1, ["~ GCP network or subnet missing"]
    except Exception as exc:
        return 1, [f"~ GCP network check failed: {exc}"]
