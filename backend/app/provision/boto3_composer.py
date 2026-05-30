# =============================================================================
# MODULE: provision/boto3_composer.py
# PURPOSE: Modular Boto3 plan/apply/destroy — mirrors terraform modules per enable_* flag.
# USED BY: boto3_deployer.py, engine_resolver.py
# =============================================================================
from __future__ import annotations

import ipaddress
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

BOTO3_SUPPORTED_MODULES = frozenset({"s3", "dynamodb", "vpc", "ec2", "iam", "cloudwatch"})

FLAG_TO_MODULE: dict[str, str] = {
    "enable_s3": "s3",
    "enable_dynamodb": "dynamodb",
    "enable_vpc": "vpc",
    "enable_ec2": "ec2",
    "enable_iam": "iam",
    "enable_cloudwatch": "cloudwatch",
}

APPLY_ORDER = ["vpc", "ec2", "iam", "cloudwatch", "s3", "dynamodb"]
DESTROY_ORDER = list(reversed(APPLY_ORDER))


@dataclass
class DeployContext:
    """Resource IDs passed between module steps."""
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group_id: Optional[str] = None
    instance_id: Optional[str] = None
    sns_topic_arn: Optional[str] = None
    role_name: Optional[str] = None


def _client(service: str, aws_creds: dict[str, str], region: str):
    return boto3.client(
        service,
        aws_access_key_id=aws_creds.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=aws_creds.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=aws_creds.get("AWS_SESSION_TOKEN") or None,
        region_name=region,
    )


def enabled_modules(config: dict) -> set[str]:
    out: set[str] = set()
    for flag, mod in FLAG_TO_MODULE.items():
        if config.get(flag):
            out.add(mod)
    return out


def boto3_can_handle(config: dict) -> tuple[bool, set[str]]:
    enabled = enabled_modules(config)
    unsupported = enabled - BOTO3_SUPPORTED_MODULES
    if config.get("enable_ec2") and not config.get("enable_vpc"):
        unsupported = unsupported | {"ec2"}
    return (len(unsupported) == 0 and len(enabled) > 0), unsupported


def plan_composed(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    mods = _ordered_enabled(config)
    if not mods:
        return {"success": False, "output": "", "error": "No modules enabled.", "resources": []}

    lines = ["Plan (boto3 — modular):", ""]
    resources: list[str] = []
    for mod in mods:
        part = _plan_module(mod, config, aws_creds, region)
        if not part["success"]:
            return part
        lines.extend(part.get("lines", []))
        resources.extend(part.get("resources", []))

    lines.extend(["", f"Plan: {len(resources)} resource(s) to add.", "", "✓ Ready to apply."])
    return {
        "success": True,
        "output": "\n".join(lines),
        "error": None,
        "has_changes": True,
        "resources": resources,
    }


def apply_composed(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext()
    steps: list[str] = []
    resources: list[str] = []

    for mod in _ordered_enabled(config):
        part = _apply_module(mod, config, aws_creds, region, ctx)
        steps.extend(part.get("steps", []))
        resources.extend(part.get("resources", []))
        if not part["success"]:
            return {
                "success": False,
                "output": "\n".join(steps),
                "error": part.get("error"),
                "resources": resources,
            }

    steps.append("")
    steps.append(f"Deployment complete ({len(resources)} resource(s)).")
    return {"success": True, "output": "\n".join(steps), "error": None, "resources": resources}


def destroy_composed(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext()
    steps: list[str] = []

    for mod in _ordered_enabled(config, destroy=True):
        part = _destroy_module(mod, config, aws_creds, region, ctx)
        steps.extend(part.get("steps", []))
        if not part["success"]:
            return {"success": False, "output": "\n".join(steps), "error": part.get("error")}

    return {"success": True, "output": "\n".join(steps), "error": None}


def _ordered_enabled(config: dict, destroy: bool = False) -> list[str]:
    enabled = enabled_modules(config)
    order = DESTROY_ORDER if destroy else APPLY_ORDER
    return [m for m in order if m in enabled]


# ── Module dispatch ──


def _plan_module(mod: str, config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    handlers = {
        "s3": _plan_s3,
        "dynamodb": _plan_dynamodb,
        "vpc": _plan_vpc,
        "ec2": _plan_ec2,
        "iam": _plan_iam,
        "cloudwatch": _plan_cloudwatch,
    }
    return handlers[mod](config, aws_creds, region)


def _apply_module(
    mod: str, config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> dict[str, Any]:
    handlers = {
        "s3": _apply_s3,
        "dynamodb": _apply_dynamodb,
        "vpc": _apply_vpc,
        "ec2": _apply_ec2,
        "iam": _apply_iam,
        "cloudwatch": _apply_cloudwatch,
    }
    return handlers[mod](config, aws_creds, region, ctx)


def _destroy_module(
    mod: str, config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> dict[str, Any]:
    handlers = {
        "s3": _destroy_s3,
        "dynamodb": _destroy_dynamodb,
        "vpc": _destroy_vpc,
        "ec2": _destroy_ec2,
        "iam": _destroy_iam,
        "cloudwatch": _destroy_cloudwatch,
    }
    return handlers[mod](config, aws_creds, region, ctx)


# ── S3 ──


def _plan_s3(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    if not bucket:
        return {"success": False, "error": "Bucket name is required when S3 is enabled."}
    s3 = _client("s3", aws_creds, region)
    try:
        s3.head_bucket(Bucket=bucket)
        return {"success": False, "error": f"S3 bucket '{bucket}' already exists in your account."}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            pass
        elif code in ("403", "Forbidden"):
            return {"success": False, "error": f"Bucket name '{bucket}' is globally taken."}
        else:
            return {"success": False, "error": str(exc)}
    return {
        "success": True,
        "lines": [f"  + aws_s3_bucket.main ({bucket}, {region})"],
        "resources": [f"aws_s3_bucket.main:{bucket}"],
    }


def _apply_s3(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    s3 = _client("s3", aws_creds, region)
    steps: list[str] = []
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        steps.append(f"✓ S3 bucket '{bucket}'")
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            },
        )
        s3.put_bucket_versioning(
            Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
        )
        tags = config.get("tags") or {}
        if tags:
            s3.put_bucket_tagging(
                Bucket=bucket,
                Tagging={"TagSet": [{"Key": k, "Value": str(v)} for k, v in tags.items()]},
            )
        return {
            "success": True,
            "steps": steps,
            "resources": [f"aws_s3_bucket.main:{bucket}"],
        }
    except ClientError as exc:
        return _aws_err(exc, steps)


def _destroy_s3(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    s3 = _client("s3", aws_creds, region)
    try:
        paginator = s3.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=bucket):
            objects = []
            for v in page.get("Versions", []) or []:
                objects.append({"Key": v["Key"], "VersionId": v["VersionId"]})
            for m in page.get("DeleteMarkers", []) or []:
                objects.append({"Key": m["Key"], "VersionId": m["VersionId"]})
            if objects:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
        s3.delete_bucket(Bucket=bucket)
        return {"success": True, "steps": [f"✓ Deleted S3 bucket '{bucket}'"]}
    except ClientError as exc:
        return _aws_err(exc, [])


# ── DynamoDB ──


def _plan_dynamodb(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    if not table:
        return {"success": False, "error": "DynamoDB table name is required."}
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.describe_table(TableName=table)
        return {"success": False, "error": f"DynamoDB table '{table}' already exists."}
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            return {"success": False, "error": str(exc)}
    return {
        "success": True,
        "lines": [f"  + aws_dynamodb_table.main ({table})"],
        "resources": [f"aws_dynamodb_table.main:{table}"],
    }


def _apply_dynamodb(
    config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    hash_key = config.get("dynamodb_hash_key", "id")
    hash_type = config.get("dynamodb_hash_key_type", "S")
    rcu = int(config.get("dynamodb_read_capacity", 5))
    wcu = int(config.get("dynamodb_write_capacity", 5))
    tags = config.get("tags") or {}
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.create_table(
            TableName=table,
            KeySchema=[{"AttributeName": hash_key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": hash_key, "AttributeType": hash_type}],
            ProvisionedThroughput={"ReadCapacityUnits": rcu, "WriteCapacityUnits": wcu},
            Tags=[{"Key": k, "Value": str(v)} for k, v in tags.items()] if tags else [],
        )
        return {
            "success": True,
            "steps": [f"✓ DynamoDB table '{table}'"],
            "resources": [f"aws_dynamodb_table.main:{table}"],
        }
    except ClientError as exc:
        return _aws_err(exc, [])


def _destroy_dynamodb(
    config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.delete_table(TableName=table)
        return {"success": True, "steps": [f"✓ Deleted DynamoDB table '{table}'"]}
    except ClientError as exc:
        return _aws_err(exc, [])


# ── VPC ──


def _plan_vpc(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    cidr = config.get("vpc_cidr", "10.0.0.0/16")
    return {
        "success": True,
        "lines": [
            f"  + aws_vpc.main ({cidr})",
            "  + aws_subnet.public, aws_subnet.private",
            "  + aws_internet_gateway.main",
        ],
        "resources": ["aws_vpc.main", "aws_subnet.public", "aws_internet_gateway.main"],
    }


def _apply_vpc(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = _client("ec2", aws_creds, region)
    cidr = config.get("vpc_cidr", "10.0.0.0/16")
    tags = config.get("tags") or {}
    tag_spec = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
    steps: list[str] = []
    try:
        vpc = ec2.create_vpc(CidrBlock=cidr)
        ctx.vpc_id = vpc["Vpc"]["VpcId"]
        if tag_spec:
            ec2.create_tags(Resources=[ctx.vpc_id], Tags=tag_spec + [{"Key": "Name", "Value": "main-vpc"}])
        ec2.get_waiter("vpc_available").wait(VpcIds=[ctx.vpc_id])

        azs = ec2.describe_availability_zones(Filter=[{"Name": "state", "Values": ["available"]}])
        names = [z["ZoneName"] for z in azs.get("AvailabilityZones", [])]
        if len(names) < 2:
            names = (names * 2)[:2]

        net = ipaddress.ip_network(cidr)
        subnets24 = list(net.subnets(new_prefix=24))
        if len(subnets24) < 3:
            return {"success": False, "error": "VPC CIDR too small for public/private subnets.", "steps": steps}
        public_cidr = str(subnets24[1])
        private_cidr = str(subnets24[2])

        pub = ec2.create_subnet(
            VpcId=ctx.vpc_id,
            CidrBlock=public_cidr,
            AvailabilityZone=names[0],
        )
        ctx.subnet_id = pub["Subnet"]["SubnetId"]
        ec2.modify_subnet_attribute(
            SubnetId=ctx.subnet_id, MapPublicIpOnLaunch={"Value": True}
        )

        ec2.create_subnet(
            VpcId=ctx.vpc_id,
            CidrBlock=private_cidr,
            AvailabilityZone=names[1],
        )

        igw = ec2.create_internet_gateway()
        ec2.attach_internet_gateway(InternetGatewayId=igw["InternetGateway"]["InternetGatewayId"], VpcId=ctx.vpc_id)
        rt = ec2.create_route_table(VpcId=ctx.vpc_id)
        ec2.create_route(
            RouteTableId=rt["RouteTable"]["RouteTableId"],
            DestinationCidrBlock="0.0.0.0/0",
            GatewayId=igw["InternetGateway"]["InternetGatewayId"],
        )
        ec2.associate_route_table(
            RouteTableId=rt["RouteTable"]["RouteTableId"], SubnetId=ctx.subnet_id
        )
        steps.append(f"✓ VPC {ctx.vpc_id} + public subnet {ctx.subnet_id}")
        return {"success": True, "steps": steps, "resources": ["aws_vpc.main"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


def _destroy_vpc(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = _client("ec2", aws_creds, region)
    steps: list[str] = []
    try:
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": ["main-vpc"]}])
        for vpc in vpcs.get("Vpcs", []):
            vpc_id = vpc["VpcId"]
            for igw in ec2.describe_internet_gateways(
                Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
            ).get("InternetGateways", []):
                ec2.detach_internet_gateway(
                    InternetGatewayId=igw["InternetGatewayId"], VpcId=vpc_id
                )
                ec2.delete_internet_gateway(InternetGatewayId=igw["InternetGatewayId"])
            for sub in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get("Subnets", []):
                for assoc in ec2.describe_route_tables(
                    Filters=[{"Name": "association.subnet-id", "Values": [sub["SubnetId"]]}]
                ).get("RouteTables", []):
                    for a in assoc.get("Associations", []):
                        if a.get("RouteTableAssociationId"):
                            ec2.disassociate_route_table(
                                AssociationId=a["RouteTableAssociationId"]
                            )
                ec2.delete_subnet(SubnetId=sub["SubnetId"])
            for rt in ec2.describe_route_tables(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            ).get("RouteTables", []):
                if not rt.get("Associations") or all(
                    not a.get("Main") for a in rt.get("Associations", [])
                ):
                    try:
                        ec2.delete_route_table(RouteTableId=rt["RouteTableId"])
                    except ClientError:
                        pass
            ec2.delete_vpc(VpcId=vpc_id)
            steps.append(f"✓ Deleted VPC {vpc_id}")
        return {"success": True, "steps": steps or ["✓ VPC cleanup done"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


# ── EC2 ──


def _plan_ec2(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    if not config.get("enable_vpc"):
        return {"success": False, "error": "EC2 requires VPC module (enable VPC)."}
    itype = config.get("instance_type", "t2.micro")
    return {
        "success": True,
        "lines": [f"  + aws_instance.main ({itype})"],
        "resources": ["aws_instance.main"],
    }


def _apply_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    if not ctx.vpc_id or not ctx.subnet_id:
        return {"success": False, "error": "EC2 apply requires VPC step first.", "steps": []}
    ec2 = _client("ec2", aws_creds, region)
    steps: list[str] = []
    try:
        sg = ec2.create_security_group(
            GroupName="zenith-ec2-sg",
            Description="Zenith EC2 security group",
            VpcId=ctx.vpc_id,
        )
        ctx.security_group_id = sg["GroupId"]
        ec2.authorize_security_group_egress(
            GroupId=ctx.security_group_id,
            IpPermissions=[
                {
                    "IpProtocol": "-1",
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "All outbound"}],
                }
            ],
        )

        ami_id = (config.get("ami_id") or "").strip()
        if not ami_id:
            images = ec2.describe_images(
                Owners=["amazon"],
                Filters=[
                    {"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-gp2"]},
                    {"Name": "state", "Values": ["available"]},
                ],
            )
            images["Images"].sort(key=lambda x: x["CreationDate"], reverse=True)
            ami_id = images["Images"][0]["ImageId"] if images["Images"] else ""

        if not ami_id:
            return {"success": False, "error": "No AMI found for this region.", "steps": steps}

        inst = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=config.get("instance_type", "t2.micro"),
            MinCount=1,
            MaxCount=1,
            SubnetId=ctx.subnet_id,
            SecurityGroupIds=[ctx.security_group_id],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": config.get("instance_name", "main-instance")}],
                }
            ],
        )
        ctx.instance_id = inst["Instances"][0]["InstanceId"]
        steps.append(f"✓ EC2 instance {ctx.instance_id}")
        return {"success": True, "steps": steps, "resources": [f"aws_instance.main:{ctx.instance_id}"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


def _destroy_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = _client("ec2", aws_creds, region)
    steps: list[str] = []
    try:
        name = config.get("instance_name", "main-instance")
        res = ec2.describe_instances(
            Filters=[{"Name": "tag:Name", "Values": [name]}, {"Name": "instance-state-name", "Values": ["pending", "running", "stopped"]}]
        )
        for r in res.get("Reservations", []):
            for i in r.get("Instances", []):
                iid = i["InstanceId"]
                ec2.terminate_instances(InstanceIds=[iid])
                steps.append(f"✓ Terminating EC2 {iid}")
        for sg in ec2.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": ["zenith-ec2-sg"]}]
        ).get("SecurityGroups", []):
            try:
                ec2.delete_security_group(GroupId=sg["GroupId"])
            except ClientError:
                pass
        return {"success": True, "steps": steps or ["✓ EC2 cleanup done"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


# ── IAM ──


def _plan_iam(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    role = config.get("role_name", "app-role")
    return {
        "success": True,
        "lines": [f"  + aws_iam_role.main ({role})"],
        "resources": [f"aws_iam_role.main:{role}"],
    }


def _apply_iam(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    iam = _client("iam", aws_creds, region)
    role_name = config.get("role_name", "app-role")
    bucket = (config.get("bucket_name") or "").strip() or "*"
    steps: list[str] = []
    try:
        trust = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust))
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-policy",
            PolicyDocument=json.dumps(policy),
        )
        iam.create_instance_profile(InstanceProfileName=f"{role_name}-profile")
        iam.add_role_to_instance_profile(
            InstanceProfileName=f"{role_name}-profile", RoleName=role_name
        )
        ctx.role_name = role_name
        steps.append(f"✓ IAM role '{role_name}'")
        return {"success": True, "steps": steps, "resources": [f"aws_iam_role.main:{role_name}"]}
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "EntityAlreadyExists":
            steps.append(f"✓ IAM role '{role_name}' (already exists)")
            ctx.role_name = role_name
            return {"success": True, "steps": steps, "resources": [f"aws_iam_role.main:{role_name}"]}
        return _aws_err(exc, steps)


def _destroy_iam(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    iam = _client("iam", aws_creds, region)
    role_name = config.get("role_name", "app-role")
    profile = f"{role_name}-profile"
    steps: list[str] = []
    try:
        try:
            iam.remove_role_from_instance_profile(
                InstanceProfileName=profile, RoleName=role_name
            )
            iam.delete_instance_profile(InstanceProfileName=profile)
        except ClientError:
            pass
        try:
            iam.delete_role_policy(RoleName=role_name, PolicyName=f"{role_name}-policy")
        except ClientError:
            pass
        try:
            iam.delete_role(RoleName=role_name)
            steps.append(f"✓ Deleted IAM role '{role_name}'")
        except ClientError:
            pass
        return {"success": True, "steps": steps or ["✓ IAM cleanup done"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


# ── CloudWatch ──


def _plan_cloudwatch(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    lines = ["  + aws_sns_topic.alerts"]
    if config.get("enable_ec2"):
        lines.append("  + aws_cloudwatch_metric_alarm.cpu_high")
    else:
        lines.append("  (CPU alarm skipped — enable EC2 for instance metrics)")
    return {"success": True, "lines": lines, "resources": ["aws_sns_topic.alerts"]}


def _apply_cloudwatch(
    config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> dict[str, Any]:
    sns = _client("sns", aws_creds, region)
    cw = _client("cloudwatch", aws_creds, region)
    steps: list[str] = []
    try:
        topic = sns.create_topic(Name="cloudwatch-alerts")
        ctx.sns_topic_arn = topic["TopicArn"]
        steps.append("✓ SNS topic cloudwatch-alerts")

        email = (config.get("alarm_email") or "").strip()
        if email:
            sns.subscribe(TopicArn=ctx.sns_topic_arn, Protocol="email", Endpoint=email)
            steps.append(f"✓ Email subscription pending for {email}")

        if config.get("enable_ec2") and ctx.instance_id:
            cw.put_metric_alarm(
                AlarmName="ec2-cpu-high",
                ComparisonOperator="GreaterThanThreshold",
                EvaluationPeriods=2,
                MetricName="CPUUtilization",
                Namespace="AWS/EC2",
                Period=300,
                Statistic="Average",
                Threshold=80.0,
                ActionsEnabled=True,
                AlarmActions=[ctx.sns_topic_arn],
                AlarmDescription="EC2 CPU utilization exceeded 80%",
                Dimensions=[{"Name": "InstanceId", "Value": ctx.instance_id}],
            )
            steps.append(f"✓ CPU alarm for instance {ctx.instance_id}")

        return {"success": True, "steps": steps, "resources": ["aws_sns_topic.alerts"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


def _destroy_cloudwatch(
    config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> dict[str, Any]:
    sns = _client("sns", aws_creds, region)
    cw = _client("cloudwatch", aws_creds, region)
    steps: list[str] = []
    try:
        try:
            cw.delete_alarms(AlarmNames=["ec2-cpu-high"])
        except ClientError:
            pass
        topics = sns.list_topics()
        for t in topics.get("Topics", []):
            if t["TopicArn"].endswith(":cloudwatch-alerts"):
                subs = sns.list_subscriptions_by_topic(TopicArn=t["TopicArn"])
                for s in subs.get("Subscriptions", []):
                    sns.unsubscribe(SubscriptionArn=s["SubscriptionArn"])
                sns.delete_topic(TopicArn=t["TopicArn"])
                steps.append("✓ Deleted SNS topic cloudwatch-alerts")
        return {"success": True, "steps": steps or ["✓ CloudWatch cleanup done"]}
    except ClientError as exc:
        return _aws_err(exc, steps)


def _aws_err(exc: ClientError, steps: list[str]) -> dict[str, Any]:
    code = exc.response.get("Error", {}).get("Code", "ClientError")
    msg = exc.response.get("Error", {}).get("Message", str(exc))
    logger.exception("boto3 module failed: %s", code)
    return {"success": False, "steps": steps, "error": f"AWS {code}: {msg}"}
