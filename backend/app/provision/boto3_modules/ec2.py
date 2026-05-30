from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import aws_err, client
from app.provision.boto3_modules.context import DeployContext

SG_NAME = "ec2-security-group"


def _resolve_ami(ec2, region: str, ami_id: str) -> str:
    if ami_id:
        return ami_id
    images = ec2.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-gp2"]},
            {"Name": "state", "Values": ["available"]},
        ],
    )
    candidates = sorted(images.get("Images", []), key=lambda x: x["CreationDate"], reverse=True)
    if not candidates:
        raise ValueError(f"No Amazon Linux 2 AMI found in {region}")
    return candidates[0]["ImageId"]


def plan_ec2(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    itype = config.get("instance_type", "t2.micro")
    lines = [
        "  + aws_security_group.ec2_sg",
        f"  + aws_instance.main ({itype})",
    ]
    return {"lines": lines, "error": None, "resources": ["aws_instance.main"]}


def apply_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    if not ctx.vpc_id or not ctx.subnet_id:
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

        ami = _resolve_ami(ec2, region, (config.get("ami_id") or "").strip())
        tags = config.get("tags") or {}
        name = config.get("instance_name", "main-instance")
        inst = ec2.run_instances(
            ImageId=ami,
            InstanceType=config.get("instance_type", "t2.micro"),
            MinCount=1,
            MaxCount=1,
            SubnetId=ctx.subnet_id,
            SecurityGroupIds=[sg_id],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": k, "Value": str(v)} for k, v in tags.items()]
                    + [{"Key": "Name", "Value": name}],
                }
            ],
        )
        ctx.instance_id = inst["Instances"][0]["InstanceId"]
        return {"success": True, "steps": [f"✓ EC2 instance {ctx.instance_id}"], "error": None}
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
