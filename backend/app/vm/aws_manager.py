"""AWS EC2 VM lifecycle for Zenith cluster pools (parity with GCP manager)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import client
from app.provision.boto3_modules.ec2 import _resolve_ami
from app.provision.provision_config_options import ec2_os_root_device, normalize_ec2_os
from app.utils.logger import setup_logger
from app.vm.aws_runtime import aws_boto_credentials, aws_region
from app.vm.cluster_catalog import (
    cluster_create_spec,
    cluster_types,
    cluster_vms as catalog_cluster_vms,
)
from app.vm.models import ClusterType

logger = setup_logger(__name__)

ZENITH_TAG = "zenith_managed"
CLUSTER_TAG = "zenith_cluster"

AWS_CLUSTER_VMS: dict[ClusterType, list[str]] = {
    ct: catalog_cluster_vms("AWS", ct) for ct in cluster_types()
}


def _ec2():
    return client("ec2", aws_boto_credentials(), aws_region())


def _map_state(aws_state: str) -> str:
    state = (aws_state or "").lower()
    if state == "running":
        return "RUNNING"
    if state in ("stopped", "stopping"):
        return "TERMINATED"
    if state in ("pending", "starting"):
        return "PROVISIONING"
    return state.upper()


def _instance_by_name(ec2, name: str) -> Optional[dict[str, Any]]:
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [name]},
            {"Name": f"tag:{ZENITH_TAG}", "Values": ["true"]},
        ]
    )
    for reservation in resp.get("Reservations", []):
        for inst in reservation.get("Instances", []):
            if inst.get("State", {}).get("Name") != "terminated":
                return inst
    return None


def _external_ip(inst: dict[str, Any]) -> str:
    return inst.get("PublicIpAddress") or "N/A"


def _tags_dict(inst: dict[str, Any]) -> dict[str, str]:
    return {t["Key"]: t["Value"] for t in inst.get("Tags", [])}


def _get_default_vpc_subnet(ec2) -> tuple[str, str]:
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    vpc_list = vpcs.get("Vpcs", [])
    if not vpc_list:
        raise ValueError(
            "No default VPC in this region. Create a default VPC or provision VPC via Terraform first."
        )
    vpc_id = vpc_list[0]["VpcId"]
    subnets = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}, {"Name": "default-for-az", "Values": ["true"]}]
    )
    subnet_list = subnets.get("Subnets", [])
    if not subnet_list:
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
        subnet_list = subnets.get("Subnets", [])
    if not subnet_list:
        raise ValueError("No subnet found in default VPC for EC2 launch.")
    for sub in subnet_list:
        if sub.get("MapPublicIpOnLaunch"):
            return vpc_id, sub["SubnetId"]
    return vpc_id, subnet_list[0]["SubnetId"]


def _default_security_group_id(ec2, vpc_id: str) -> Optional[str]:
    groups = ec2.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "group-name", "Values": ["default"]},
        ]
    ).get("SecurityGroups", [])
    return groups[0]["GroupId"] if groups else None


def _resolve_vm_ami(ec2, region: str, source_image: str = "") -> tuple[str, str]:
    """
    Resolve AMI id and root device for VM cluster launches.

    ``source_image`` may be an AMI id (``ami-…``), an EC2_OS_IMAGES key, or empty for default.
    """
    src = (source_image or "").strip()
    config: dict[str, str] = {}
    if src.startswith("ami-"):
        config["ami_id"] = src
        os_key = "ubuntu_22_04"
    elif src:
        os_key = normalize_ec2_os(src)
        config["ec2_os"] = os_key
    else:
        os_key = "ubuntu_22_04"
        config["ec2_os"] = os_key
    ami_id = _resolve_ami(ec2, region, config)
    root_device = ec2_os_root_device(os_key)
    return ami_id, root_device


def list_vms() -> List[Dict[str, Any]]:
    try:
        ec2 = _ec2()
        resp = ec2.describe_instances(
            Filters=[{"Name": f"tag:{ZENITH_TAG}", "Values": ["true"]}]
        )
        vms: list[dict[str, Any]] = []
        for reservation in resp.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                state = inst.get("State", {}).get("Name", "unknown")
                if state == "terminated":
                    continue
                tags = _tags_dict(inst)
                name = tags.get("Name", inst.get("InstanceId", "unknown"))
                vms.append(
                    {
                        "name": name,
                        "status": _map_state(state),
                        "machine_type": inst.get("InstanceType", "unknown"),
                        "zone": inst.get("Placement", {}).get("AvailabilityZone", aws_region()),
                        "labels": {
                            "cluster_type": tags.get(CLUSTER_TAG, "general"),
                            ZENITH_TAG: "true",
                        },
                        "creation_timestamp": (
                            inst.get("LaunchTime").isoformat()
                            if inst.get("LaunchTime")
                            else None
                        ),
                        "network_interfaces": [
                            {
                                "network_ip": inst.get("PrivateIpAddress"),
                                "external_ip": _external_ip(inst),
                            }
                        ],
                        "instance_id": inst.get("InstanceId"),
                    }
                )
        return vms
    except Exception as exc:
        logger.error("Error listing AWS VMs: %s", exc)
        return []


def get_vm_details(name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    try:
        ec2 = _ec2()
        inst = _instance_by_name(ec2, name)
        if not inst:
            return {
                "name": name,
                "status": "UNKNOWN",
                "machine_type": "unknown",
                "zone": zone or aws_region(),
                "external_ip": "N/A",
                "creation_timestamp": None,
                "labels": {},
            }
        tags = _tags_dict(inst)
        return {
            "name": tags.get("Name", name),
            "status": _map_state(inst.get("State", {}).get("Name", "")),
            "machine_type": inst.get("InstanceType", "unknown"),
            "zone": inst.get("Placement", {}).get("AvailabilityZone", zone or aws_region()),
            "external_ip": _external_ip(inst),
            "creation_timestamp": (
                inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else None
            ),
            "labels": {"cluster_type": tags.get(CLUSTER_TAG, "general")},
            "instance_id": inst.get("InstanceId"),
        }
    except Exception as exc:
        logger.error("Error fetching AWS VM %s: %s", name, exc)
        return {
            "name": name,
            "status": "UNKNOWN",
            "machine_type": "unknown",
            "zone": zone or aws_region(),
            "external_ip": "N/A",
            "creation_timestamp": None,
            "labels": {},
        }


def create_vm(
    name: str,
    machine_type: str,
    source_image: str = "",
    disk_size_gb: int = 8,
    labels: Optional[Dict[str, str]] = None,
    *,
    disk_type: str = "",
    disk_iops: Optional[int] = None,
) -> Dict[str, Any]:
    ec2 = _ec2()
    region = aws_region()
    existing = _instance_by_name(ec2, name)
    if existing:
        return {
            "name": name,
            "status": _map_state(existing.get("State", {}).get("Name", "")),
            "details": get_vm_details(name, region),
        }

    vpc_id, subnet_id = _get_default_vpc_subnet(ec2)
    ami_id, root_device = _resolve_vm_ami(ec2, region, source_image)
    sg_id = _default_security_group_id(ec2, vpc_id)
    cluster = (labels or {}).get("cluster_type", "general")
    tags = [
        {"Key": "Name", "Value": name},
        {"Key": ZENITH_TAG, "Value": "true"},
        {"Key": CLUSTER_TAG, "Value": cluster},
    ]
    for key, value in (labels or {}).items():
        if key not in ("Name", ZENITH_TAG, CLUSTER_TAG):
            tags.append({"Key": key, "Value": str(value)})

    network_interface: dict[str, Any] = {
        "SubnetId": subnet_id,
        "DeviceIndex": 0,
        "AssociatePublicIpAddress": True,
    }
    if sg_id:
        network_interface["Groups"] = [sg_id]

    try:
        volume_type = disk_type or "gp3"
        ebs: dict[str, Any] = {
            "VolumeSize": max(8, int(disk_size_gb)),
            "VolumeType": volume_type,
            "DeleteOnTermination": True,
        }
        if disk_iops and volume_type in ("gp3", "io2", "io1"):
            ebs["Iops"] = disk_iops
        resp = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=machine_type,
            MinCount=1,
            MaxCount=1,
            NetworkInterfaces=[network_interface],
            BlockDeviceMappings=[
                {
                    "DeviceName": root_device,
                    "Ebs": ebs,
                }
            ],
            TagSpecifications=[{"ResourceType": "instance", "Tags": tags}],
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        raise ValueError(f"AWS EC2 launch failed ({code}): {msg}") from exc
    instance_ids = [i["InstanceId"] for i in resp.get("Instances", [])]
    if not instance_ids:
        raise ValueError("EC2 RunInstances returned no instances")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=instance_ids)
    details = get_vm_details(name, region)
    return {"name": name, "status": "RUNNING", "details": details}


def start_vm(name: str) -> Dict[str, Any]:
    ec2 = _ec2()
    inst = _instance_by_name(ec2, name)
    if not inst:
        raise ValueError(f"AWS instance '{name}' not found")
    iid = inst["InstanceId"]
    state = inst.get("State", {}).get("Name", "")
    if state == "stopped":
        ec2.start_instances(InstanceIds=[iid])
        ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    details = get_vm_details(name, aws_region())
    return {"name": name, "status": "RUNNING", "details": details}


def stop_vm(name: str) -> Dict[str, Any]:
    ec2 = _ec2()
    inst = _instance_by_name(ec2, name)
    if not inst:
        raise ValueError(f"AWS instance '{name}' not found")
    iid = inst["InstanceId"]
    state = inst.get("State", {}).get("Name", "")
    if state == "running":
        ec2.stop_instances(InstanceIds=[iid])
        ec2.get_waiter("instance_stopped").wait(InstanceIds=[iid])
    details = get_vm_details(name, aws_region())
    return {"name": name, "status": "TERMINATED", "details": details}


def delete_vm(name: str) -> Dict[str, Any]:
    ec2 = _ec2()
    inst = _instance_by_name(ec2, name)
    if not inst:
        return {"name": name, "status": "DELETED"}
    instance_id = inst["InstanceId"]
    ec2.terminate_instances(InstanceIds=[instance_id])
    try:
        ec2.get_waiter("instance_terminated").wait(InstanceIds=[instance_id])
    except Exception as exc:
        logger.debug("Waiting for %s termination: %s", name, exc)
    return {"name": name, "status": "DELETED"}


def cluster_machine_type(cluster_type: ClusterType, slot_id: Optional[str] = None) -> str:
    return cluster_create_spec("AWS", cluster_type, slot_id).machine_type


def cluster_disk_gb(cluster_type: ClusterType, slot_id: Optional[str] = None) -> int:
    return cluster_create_spec("AWS", cluster_type, slot_id).disk_gb


def aws_configured() -> bool:
    creds = aws_boto_credentials()
    return bool(creds.get("AWS_ACCESS_KEY_ID") and creds.get("AWS_SECRET_ACCESS_KEY"))
