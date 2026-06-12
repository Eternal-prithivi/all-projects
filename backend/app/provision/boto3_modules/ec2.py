from __future__ import annotations

import time
from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import (
    PUBLIC_SUBNET_CIDR_SLOTS,
    aws_err,
    cidr_subnet,
    client,
    ec2_instance_types_to_try,
    is_ec2_capacity_error,
)
from app.provision.boto3_modules.context import DeployContext
from app.provision.provision_config_options import (
    EC2_OS_IMAGES,
    ec2_os_root_device,
    normalize_ec2_os,
    normalize_user_data,
)

SG_NAME = "ec2-security-group"


def _resolve_ami(ec2, region: str, config: dict) -> str:
    ami_id = (config.get("ami_id") or "").strip()
    if ami_id:
        return ami_id
    os_key = normalize_ec2_os(config.get("ec2_os"))
    os_meta = EC2_OS_IMAGES[os_key]
    images = ec2.describe_images(
        Owners=os_meta["owners"],
        Filters=[
            {"Name": "name", "Values": [os_meta["name_filter"]]},
            {"Name": "state", "Values": ["available"]},
        ],
    )
    candidates = sorted(images.get("Images", []), key=lambda x: x["CreationDate"], reverse=True)
    if not candidates:
        raise ValueError(f"No {os_meta['label']} AMI found in {region}")
    return candidates[0]["ImageId"]


def _public_subnet_candidates(ec2, ctx: DeployContext) -> list[str]:
    if ctx.public_subnet_ids:
        return list(ctx.public_subnet_ids)
    if ctx.subnet_id:
        return [ctx.subnet_id]
    if not ctx.vpc_id:
        return []
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [ctx.vpc_id]}]).get(
        "Subnets", []
    )
    public_ids: list[str] = []
    for sub in subnets:
        sid = sub["SubnetId"]
        attrs = ec2.describe_subnet_attribute(SubnetId=sid, Attribute="mapPublicIpOnLaunch")
        if attrs.get("MapPublicIpOnLaunch", {}).get("Value"):
            public_ids.append(sid)
    return public_ids


def _subnet_az(ec2, subnet_id: str) -> str:
    subs = ec2.describe_subnets(SubnetIds=[subnet_id]).get("Subnets", [])
    if subs:
        return subs[0].get("AvailabilityZone", "")
    return ""


def _public_route_table_id(ec2, vpc_id: str) -> str | None:
    for rt in ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    ).get("RouteTables", []):
        for route in rt.get("Routes", []):
            if str(route.get("GatewayId", "")).startswith("igw-"):
                return rt["RouteTableId"]
    return None


def _next_free_subnet_cidr(ec2, vpc_id: str, base_cidr: str) -> str | None:
    used = {
        s["CidrBlock"]
        for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get(
            "Subnets", []
        )
    }
    for slot in PUBLIC_SUBNET_CIDR_SLOTS + (11, 13, 15, 17):
        candidate = cidr_subnet(base_cidr, 8, slot)
        if candidate not in used:
            return candidate
    return None


def _add_public_subnet_in_unused_az(
    ec2,
    ctx: DeployContext,
    config: dict,
) -> str | None:
    """Legacy VPCs may have one public subnet; add another AZ before giving up."""
    if not ctx.vpc_id:
        return None
    azs = [
        z["ZoneName"]
        for z in ec2.describe_availability_zones(
            Filters=[{"Name": "state", "Values": ["available"]}]
        ).get("AvailabilityZones", [])
    ]
    if not azs:
        return None

    used_azs = {_subnet_az(ec2, sid) for sid in _public_subnet_candidates(ec2, ctx)}
    target_az = next((az for az in azs if az not in used_azs), None)
    if not target_az:
        return None

    cidr_block = _next_free_subnet_cidr(ec2, ctx.vpc_id, config.get("vpc_cidr", "10.0.0.0/16"))
    rt_id = _public_route_table_id(ec2, ctx.vpc_id)
    if not cidr_block or not rt_id:
        return None

    pub = ec2.create_subnet(
        VpcId=ctx.vpc_id,
        CidrBlock=cidr_block,
        AvailabilityZone=target_az,
        TagSpecifications=[
            {
                "ResourceType": "subnet",
                "Tags": [{"Key": "Name", "Value": f"public-subnet-{target_az}"}],
            }
        ],
    )
    subnet_id = pub["Subnet"]["SubnetId"]
    ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True})
    ec2.associate_route_table(RouteTableId=rt_id, SubnetId=subnet_id)
    ctx.public_subnet_ids = list(_public_subnet_candidates(ec2, ctx)) + [subnet_id]
    return subnet_id


def _run_instances_resilient(
    ec2,
    *,
    config: dict,
    region: str,
    ctx: DeployContext,
    sg_id: str,
    ami: str,
) -> dict[str, Any]:
    """Try public subnets and free-tier instance types until launch succeeds."""
    subnet_ids = _public_subnet_candidates(ec2, ctx)
    if not subnet_ids:
        return {
            "success": False,
            "error": "No public subnets available for EC2 launch.",
        }

    instance_types = ec2_instance_types_to_try(config.get("instance_type", "t2.micro"))
    tags = config.get("tags") or {}
    name = config.get("instance_name", "main-instance")
    disk_gb = max(8, min(int(config.get("disk_size_gb") or 30), 2000))
    root_device = ec2_os_root_device(config.get("ec2_os"))
    user_data = normalize_user_data(config.get("ec2_user_data"), config.get("ec2_os"))
    tag_specs = [
        {
            "ResourceType": "instance",
            "Tags": [{"Key": k, "Value": str(v)} for k, v in tags.items()]
            + [{"Key": "Name", "Value": name}],
        }
    ]

    attempts: list[str] = []
    last_error = "EC2 launch failed in all availability zones."

    def _attempt_launch(subnet_id: str) -> dict[str, Any] | None:
        nonlocal last_error
        az = _subnet_az(ec2, subnet_id)
        for instance_type in instance_types:
            attempts.append(f"{instance_type}@{az or subnet_id}")
            try:
                run_kwargs: dict[str, Any] = {
                    "ImageId": ami,
                    "InstanceType": instance_type,
                    "MinCount": 1,
                    "MaxCount": 1,
                    "SubnetId": subnet_id,
                    "SecurityGroupIds": [sg_id],
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": root_device,
                            "Ebs": {
                                "VolumeSize": disk_gb,
                                "DeleteOnTermination": True,
                                "VolumeType": "gp3",
                            },
                        }
                    ],
                    "TagSpecifications": tag_specs,
                }
                if user_data:
                    run_kwargs["UserData"] = user_data
                if ctx.instance_profile_name:
                    run_kwargs["IamInstanceProfile"] = {"Name": ctx.instance_profile_name}
                inst = ec2.run_instances(**run_kwargs)
                ctx.subnet_id = subnet_id
                ctx.launch_availability_zone = az or None
                ctx.launched_instance_type = instance_type
                ctx.instance_id = inst["Instances"][0]["InstanceId"]
                note_parts = [f"✓ EC2 {ctx.instance_id}"]
                if instance_type != config.get("instance_type", "t2.micro"):
                    note_parts.append(
                        f"(used {instance_type} — {config.get('instance_type', 't2.micro')} unavailable)"
                    )
                if az:
                    note_parts.append(f"in {az}")
                return {
                    "success": True,
                    "steps": [" ".join(note_parts)],
                    "error": None,
                }
            except ClientError as exc:
                if is_ec2_capacity_error(exc):
                    last_error = aws_err(exc)
                    continue
                return {"success": False, "error": aws_err(exc)}
        return None

    for subnet_id in subnet_ids:
        hit = _attempt_launch(subnet_id)
        if hit:
            return hit

    extra_subnet = _add_public_subnet_in_unused_az(ec2, ctx, config)
    if extra_subnet:
        hit = _attempt_launch(extra_subnet)
        if hit:
            return hit

    return {
        "success": False,
        "error": (
            f"{last_error} Tried: {', '.join(attempts)}. "
            "AWS is out of capacity for free-tier types in this region — retry later or pick another region."
        ),
    }


def plan_ec2(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    itype = config.get("instance_type", "t2.micro")
    os_key = normalize_ec2_os(config.get("ec2_os"))
    os_label = EC2_OS_IMAGES[os_key]["label"]
    lines = [
        "  + aws_security_group.ec2_sg",
        f"  + aws_instance.main ({itype}, {os_label}, multi-AZ fallback)",
    ]
    if (config.get("ec2_user_data") or "").strip():
        lines.append("  + user_data bootstrap script")
    if config.get("enable_iam"):
        lines.append("  + IAM instance profile attached at launch")
    return {"lines": lines, "error": None, "resources": ["aws_instance.main"]}


def apply_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    if not ctx.vpc_id or not (ctx.subnet_id or ctx.public_subnet_ids):
        return {"success": False, "steps": [], "error": "EC2 requires VPC (enable VPC module)."}
    ec2 = client("ec2", aws_creds, region)
    try:
        sg_id = None
        for sg_name in (SG_NAME, f"{SG_NAME}-zenith"):
            try:
                sg = ec2.create_security_group(
                    GroupName=sg_name,
                    Description="Security group for EC2 instance. No unrestricted inbound access.",
                    VpcId=ctx.vpc_id,
                )
                sg_id = sg["GroupId"]
                break
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") == "InvalidGroup.Duplicate":
                    existing = ec2.describe_security_groups(
                        Filters=[
                            {"Name": "group-name", "Values": [sg_name]},
                            {"Name": "vpc-id", "Values": [ctx.vpc_id]},
                        ]
                    )
                    groups = existing.get("SecurityGroups", [])
                    if groups:
                        sg_id = groups[0]["GroupId"]
                        break
                raise

        if not sg_id:
            return {"success": False, "steps": [], "error": "Could not create or find EC2 security group."}

        ctx.security_group_id = sg_id
        try:
            ec2.authorize_security_group_egress(
                GroupId=sg_id,
                IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "InvalidPermission.Duplicate":
                raise

        ctx.ec2_os = normalize_ec2_os(config.get("ec2_os"))
        ami = _resolve_ami(ec2, region, config)
        launch = _run_instances_resilient(
            ec2, config=config, region=region, ctx=ctx, sg_id=sg_id, ami=ami
        )
        if not launch.get("success"):
            return {"success": False, "steps": [], "error": launch.get("error")}

        for _ in range(24):
            desc = ec2.describe_instances(InstanceIds=[ctx.instance_id])
            reservations = desc.get("Reservations") or []
            if reservations and reservations[0].get("Instances"):
                pub = reservations[0]["Instances"][0].get("PublicIpAddress")
                if pub:
                    ctx.public_ip = pub
                    break
            time.sleep(2)

        steps = list(launch.get("steps") or [])
        if ctx.public_ip:
            steps[0] = f"{steps[0]} ({ctx.public_ip})"
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": aws_err(exc)}


def destroy_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = client("ec2", aws_creds, region)
    steps: list[str] = []
    try:
        if ctx.instance_id:
            ec2.terminate_instances(InstanceIds=[ctx.instance_id])
            waiter = ec2.get_waiter("instance_terminated")
            waiter.wait(InstanceIds=[ctx.instance_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
            steps.append(f"✓ Terminated instance {ctx.instance_id}")
        if ctx.security_group_id:
            try:
                ec2.delete_security_group(GroupId=ctx.security_group_id)
                steps.append("✓ Deleted security group")
            except ClientError:
                pass
        return {"success": True, "steps": steps or ["EC2: nothing to delete"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": aws_err(exc)}
