"""AWS EC2 VM lifecycle for Zenith cluster pools (parity with GCP manager)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import client
from app.provision.boto3_modules.ec2 import _resolve_ami
from app.utils.logger import setup_logger
from app.vm.aws_runtime import aws_boto_credentials, aws_region
from app.vm.models import ClusterType

logger = setup_logger(__name__)

ZENITH_TAG = "zenith_managed"
CLUSTER_TAG = "zenith_cluster"

AWS_CLUSTER_VMS: dict[ClusterType, list[str]] = {
    ClusterType.GENERAL: ["general-aws-vm-1", "general-aws-vm-2"],
    ClusterType.STORAGE: ["storage-aws-vm-1", "storage-aws-vm-2"],
    ClusterType.MEMORY: ["memory-aws-vm-1", "memory-aws-vm-2"],
    ClusterType.PERFORMANCE: ["performance-aws-vm-1", "performance-aws-vm-2"],
    ClusterType.AI_ML: ["ai-ml-aws-vm-1", "ai-ml-aws-vm-2"],
}

_CLUSTER_INSTANCE_TYPES: dict[str, str] = {
    "general": "t2.micro",
    "storage": "t2.small",
    "memory": "t2.small",
    "performance": "t2.medium",
    "ai_ml": "t2.medium",
}

_CLUSTER_DISK_GB: dict[str, int] = {
    "general": 8,
    "storage": 20,
    "memory": 16,
    "performance": 30,
    "ai_ml": 40,
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
    return vpc_id, subnet_list[0]["SubnetId"]


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
        raise


def create_vm(
    name: str,
    machine_type: str,
    source_image: str = "",
    disk_size_gb: int = 8,
    labels: Optional[Dict[str, str]] = None,
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
    ami_id = _resolve_ami(ec2, region, (source_image or "").strip())
    cluster = (labels or {}).get("cluster_type", "general")
    tags = [
        {"Key": "Name", "Value": name},
        {"Key": ZENITH_TAG, "Value": "true"},
        {"Key": CLUSTER_TAG, "Value": cluster},
    ]
    for key, value in (labels or {}).items():
        if key not in ("Name", ZENITH_TAG, CLUSTER_TAG):
            tags.append({"Key": key, "Value": str(value)})

    resp = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=machine_type,
        MinCount=1,
        MaxCount=1,
        SubnetId=subnet_id,
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}],
    )
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
    ec2.terminate_instances(InstanceIds=[inst["InstanceId"]])
    return {"name": name, "status": "DELETED"}


def cluster_machine_type(cluster_type: ClusterType) -> str:
    return _CLUSTER_INSTANCE_TYPES.get(cluster_type.value, "t2.micro")


def cluster_disk_gb(cluster_type: ClusterType) -> int:
    return _CLUSTER_DISK_GB.get(cluster_type.value, 8)


def aws_configured() -> bool:
    creds = aws_boto_credentials()
    return bool(creds.get("AWS_ACCESS_KEY_ID") and creds.get("AWS_SECRET_ACCESS_KEY"))
