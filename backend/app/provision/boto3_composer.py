# =============================================================================
# MODULE: provision/boto3_composer.py
# PURPOSE: Module-composed AWS deploys via boto3 (no Terraform CLI).
# Parity with backend/terraform/modules/* for plan/apply/destroy + drift checks.
# Works on localhost and Render free tier (low RAM, no terraform init).
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

BOTO3_IMPLEMENTED = frozenset({"s3", "dynamodb", "vpc", "ec2", "iam", "cloudwatch"})

MODULE_FLAGS: dict[str, str] = {
    "s3": "enable_s3",
    "dynamodb": "enable_dynamodb",
    "vpc": "enable_vpc",
    "ec2": "enable_ec2",
    "iam": "enable_iam",
    "cloudwatch": "enable_cloudwatch",
}

APPLY_ORDER = ("vpc", "ec2", "iam", "cloudwatch", "s3", "dynamodb")
DESTROY_ORDER = ("dynamodb", "s3", "cloudwatch", "iam", "ec2", "vpc")


@dataclass
class DeployContext:
    """Resource IDs passed between modules during apply/destroy."""

    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    instance_id: Optional[str] = None
    security_group_id: Optional[str] = None
    role_arn: Optional[str] = None
    sns_topic_arn: Optional[str] = None
    bucket_name: Optional[str] = None
    dynamodb_table: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, val in (
            ("vpc_id", self.vpc_id),
            ("subnet_id", self.subnet_id),
            ("instance_id", self.instance_id),
            ("security_group_id", self.security_group_id),
            ("role_arn", self.role_arn),
            ("sns_topic_arn", self.sns_topic_arn),
            ("bucket_name", self.bucket_name),
            ("dynamodb_table", self.dynamodb_table),
        ):
            if val:
                out[key] = val
        return out

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> DeployContext:
        if not data:
            return cls()
        return cls(
            vpc_id=data.get("vpc_id"),
            subnet_id=data.get("subnet_id"),
            instance_id=data.get("instance_id"),
            security_group_id=data.get("security_group_id"),
            role_arn=data.get("role_arn"),
            sns_topic_arn=data.get("sns_topic_arn"),
            bucket_name=data.get("bucket_name"),
            dynamodb_table=data.get("dynamodb_table"),
        )


def _client(service: str, aws_creds: dict[str, str], region: Optional[str] = None):
    region = region or aws_creds.get("AWS_DEFAULT_REGION") or "ap-south-1"
    return boto3.client(
        service,
        aws_access_key_id=aws_creds.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=aws_creds.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=aws_creds.get("AWS_SESSION_TOKEN") or None,
        region_name=region,
    )


def enabled_modules(config: dict) -> set[str]:
    out: set[str] = set()
    for mod, flag in MODULE_FLAGS.items():
        if config.get(flag):
            out.add(mod)
    return out


def boto3_can_handle(config: dict) -> tuple[bool, set[str]]:
    """Return (ok, unsupported_module_names)."""
    enabled = enabled_modules(config)
    unsupported: set[str] = set()
    if "ec2" in enabled and "vpc" not in enabled:
        unsupported.add("vpc")
    unsupported |= enabled - BOTO3_IMPLEMENTED
    return (len(unsupported) == 0 and len(enabled) > 0, unsupported)


def _cidr_subnet(base_cidr: str, new_bits: int, netnum: int) -> str:
    network = ipaddress.ip_network(base_cidr, strict=False)
    subnets = list(network.subnets(new_prefix=network.prefixlen + new_bits))
    return str(subnets[netnum])


# ── Plan / apply / destroy per module ──


def _plan_s3(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    if not bucket:
        return {"lines": [], "error": "Bucket name is required for S3.", "resources": []}
    s3 = _client("s3", aws_creds, region)
    try:
        s3.head_bucket(Bucket=bucket)
        return {"lines": [], "error": f"S3 bucket '{bucket}' already exists.", "resources": []}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            pass
        elif code in ("403", "Forbidden"):
            return {
                "lines": [],
                "error": f"Bucket name '{bucket}' is taken globally. Pick another name.",
                "resources": [],
            }
        else:
            return {"lines": [], "error": str(exc), "resources": []}
    lines = [
        f"  + aws_s3_bucket.main ({bucket}, {region})",
        "  + aws_s3_bucket_public_access_block.main",
        "  + aws_s3_bucket_server_side_encryption_configuration.main",
        "  + aws_s3_bucket_versioning.main",
    ]
    return {
        "lines": lines,
        "error": None,
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
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        tags = config.get("tags") or {}
        if tags:
            try:
                s3.put_bucket_tagging(
                    Bucket=bucket,
                    Tagging={"TagSet": [{"Key": k, "Value": str(v)} for k, v in tags.items()]},
                )
            except ClientError:
                pass
        ctx.bucket_name = bucket
        steps.append(f"✓ S3 bucket '{bucket}'")
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": _aws_err(exc)}


def _destroy_s3(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or ctx.bucket_name or "").strip()
    if not bucket:
        return {"success": True, "steps": ["S3: nothing to delete"], "error": None}
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
        return {"success": True, "steps": [f"✓ Deleted S3 bucket '{bucket}'"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _plan_dynamodb(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    if not table:
        return {"lines": [], "error": "DynamoDB table name is required.", "resources": []}
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.describe_table(TableName=table)
        return {"lines": [], "error": f"DynamoDB table '{table}' already exists.", "resources": []}
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            return {"lines": [], "error": str(exc), "resources": []}
    return {
        "lines": [f"  + aws_dynamodb_table.main ({table})"],
        "error": None,
        "resources": [f"aws_dynamodb_table.main:{table}"],
    }


def _apply_dynamodb(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
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
        ctx.dynamodb_table = table
        return {"success": True, "steps": [f"✓ DynamoDB table '{table}'"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _destroy_dynamodb(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or ctx.dynamodb_table or "").strip()
    if not table:
        return {"success": True, "steps": ["DynamoDB: nothing to delete"], "error": None}
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.delete_table(TableName=table)
        return {"success": True, "steps": [f"✓ Deleted DynamoDB table '{table}'"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _plan_vpc(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    cidr = config.get("vpc_cidr", "10.0.0.0/16")
    lines = [
        f"  + aws_vpc.main ({cidr})",
        "  + aws_subnet.public / private",
        "  + aws_internet_gateway.main",
        "  + aws_route_table.public",
    ]
    return {"lines": lines, "error": None, "resources": ["aws_vpc.main"]}


def _apply_vpc(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = _client("ec2", aws_creds, region)
    cidr = config.get("vpc_cidr", "10.0.0.0/16")
    tags = config.get("tags") or {}
    tag_specs = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
    try:
        vpc = ec2.create_vpc(CidrBlock=cidr)
        vpc_id = vpc["Vpc"]["VpcId"]
        ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": "main-vpc"}])
        ctx.vpc_id = vpc_id

        azs = ec2.describe_availability_zones(Filter=[{"Name": "state", "Values": ["available"]}])
        names = [z["ZoneName"] for z in azs.get("AvailabilityZones", [])]
        az0 = names[0] if names else f"{region}a"
        az1 = names[1] if len(names) > 1 else az0

        pub_cidr = _cidr_subnet(cidr, 8, 1)
        priv_cidr = _cidr_subnet(cidr, 8, 2)

        pub = ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=pub_cidr,
            AvailabilityZone=az0,
            TagSpecifications=[{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": "public-subnet"}]}],
        )
        ctx.subnet_id = pub["Subnet"]["SubnetId"]

        ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=priv_cidr,
            AvailabilityZone=az1,
            TagSpecifications=[{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": "private-subnet"}]}],
        )

        igw = ec2.create_internet_gateway(
            TagSpecifications=[{"ResourceType": "internet-gateway", "Tags": [{"Key": "Name", "Value": "main-igw"}]}],
        )
        igw_id = igw["InternetGateway"]["InternetGatewayId"]
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

        rt = ec2.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=[{"ResourceType": "route-table", "Tags": [{"Key": "Name", "Value": "public-rt"}]}],
        )
        rt_id = rt["RouteTable"]["RouteTableId"]
        ec2.create_route(RouteTableId=rt_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id)
        ec2.associate_route_table(RouteTableId=rt_id, SubnetId=ctx.subnet_id)

        return {"success": True, "steps": [f"✓ VPC {vpc_id} + subnets + IGW"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _destroy_vpc(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    if not ctx.vpc_id:
        return {"success": True, "steps": ["VPC: nothing to delete"], "error": None}
    ec2 = _client("ec2", aws_creds, region)
    vpc_id = ctx.vpc_id
    try:
        for rt in ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get("RouteTables", []):
            for assoc in rt.get("Associations", []):
                if not assoc.get("Main"):
                    try:
                        ec2.disassociate_route_table(AssociationId=assoc["RouteTableAssociationId"])
                    except ClientError:
                        pass
            try:
                ec2.delete_route_table(RouteTableId=rt["RouteTableId"])
            except ClientError:
                pass
        for igw in ec2.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
        ).get("InternetGateways", []):
            igw_id = igw["InternetGatewayId"]
            ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
            ec2.delete_internet_gateway(InternetGatewayId=igw_id)
        for sub in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get("Subnets", []):
            ec2.delete_subnet(SubnetId=sub["SubnetId"])
        ec2.delete_vpc(VpcId=vpc_id)
        return {"success": True, "steps": [f"✓ Deleted VPC {vpc_id}"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


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


def _plan_ec2(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    itype = config.get("instance_type", "t2.micro")
    lines = [
        f"  + aws_security_group.ec2_sg",
        f"  + aws_instance.main ({itype})",
    ]
    return {"lines": lines, "error": None, "resources": ["aws_instance.main"]}


def _apply_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    if not ctx.vpc_id or not ctx.subnet_id:
        return {"success": False, "steps": [], "error": "EC2 requires VPC (enable VPC module)."}
    ec2 = _client("ec2", aws_creds, region)
    try:
        import time

        sg_name = f"zenith-ec2-sg-{int(time.time())}"
        sg = ec2.create_security_group(
            GroupName=sg_name,
            Description="Zenith EC2 security group",
            VpcId=ctx.vpc_id,
        )
        sg_id = sg["GroupId"]
        ctx.security_group_id = sg_id
        ec2.authorize_security_group_egress(
            GroupId=sg_id,
            IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
        )

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
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _destroy_ec2(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = _client("ec2", aws_creds, region)
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
        return {"success": False, "steps": steps, "error": _aws_err(exc)}


def _plan_iam(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    role = config.get("role_name", "app-role")
    return {
        "lines": [f"  + aws_iam_role.main ({role})", f"  + aws_iam_role_policy.main"],
        "error": None,
        "resources": [f"aws_iam_role.main:{role}"],
    }


def _apply_iam(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    iam = _client("iam", aws_creds, region)
    role_name = config.get("role_name", "app-role")
    bucket = (config.get("bucket_name") or "").strip() or "*"
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
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust),
            Tags=[{"Key": k, "Value": str(v)} for k, v in (config.get("tags") or {}).items()],
        )
        ctx.role_arn = role["Role"]["Arn"]
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-policy",
            PolicyDocument=json.dumps(policy),
        )
        return {"success": True, "steps": [f"✓ IAM role '{role_name}'"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _destroy_iam(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    iam = _client("iam", aws_creds, region)
    role_name = config.get("role_name", "app-role")
    try:
        iam.delete_role_policy(RoleName=role_name, PolicyName=f"{role_name}-policy")
    except ClientError:
        pass
    try:
        iam.delete_role(RoleName=role_name)
        return {"success": True, "steps": [f"✓ Deleted IAM role '{role_name}'"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _plan_cloudwatch(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    lines = ["  + aws_sns_topic.alerts"]
    if config.get("enable_ec2"):
        lines.append("  + aws_cloudwatch_metric_alarm.cpu_high")
    elif config.get("alarm_email"):
        lines.append("  + aws_sns_topic_subscription.email")
    return {"lines": lines, "error": None, "resources": ["aws_sns_topic.alerts"]}


def _apply_cloudwatch(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    sns = _client("sns", aws_creds, region)
    cw = _client("cloudwatch", aws_creds, region)
    email = (config.get("alarm_email") or "").strip()
    try:
        topic = sns.create_topic(Name="zenith-cloudwatch-alerts")
        arn = topic["TopicArn"]
        ctx.sns_topic_arn = arn
        steps = [f"✓ SNS topic {arn}"]
        if email:
            sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=email)
            steps.append(f"✓ Email subscription pending for {email}")
        if config.get("enable_ec2") and ctx.instance_id:
            cw.put_metric_alarm(
                AlarmName="zenith-ec2-cpu-high",
                ComparisonOperator="GreaterThanThreshold",
                EvaluationPeriods=2,
                MetricName="CPUUtilization",
                Namespace="AWS/EC2",
                Period=300,
                Statistic="Average",
                Threshold=80.0,
                AlarmActions=[arn],
                Dimensions=[{"Name": "InstanceId", "Value": ctx.instance_id}],
            )
            steps.append(f"✓ CPU alarm on instance {ctx.instance_id}")
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": _aws_err(exc)}


def _destroy_cloudwatch(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    cw = _client("cloudwatch", aws_creds, region)
    sns = _client("sns", aws_creds, region)
    steps: list[str] = []
    try:
        try:
            cw.delete_alarms(AlarmNames=["zenith-ec2-cpu-high"])
            steps.append("✓ Deleted CPU alarm")
        except ClientError:
            pass
        if ctx.sns_topic_arn:
            sns.delete_topic(TopicArn=ctx.sns_topic_arn)
            steps.append("✓ Deleted SNS topic")
        return {"success": True, "steps": steps or ["CloudWatch: nothing to delete"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": _aws_err(exc)}


_PLAN_HANDLERS = {
    "s3": _plan_s3,
    "dynamodb": _plan_dynamodb,
    "vpc": _plan_vpc,
    "ec2": _plan_ec2,
    "iam": _plan_iam,
    "cloudwatch": _plan_cloudwatch,
}
_APPLY_HANDLERS = {
    "s3": _apply_s3,
    "dynamodb": _apply_dynamodb,
    "vpc": _apply_vpc,
    "ec2": _apply_ec2,
    "iam": _apply_iam,
    "cloudwatch": _apply_cloudwatch,
}
_DESTROY_HANDLERS = {
    "s3": _destroy_s3,
    "dynamodb": _destroy_dynamodb,
    "vpc": _destroy_vpc,
    "ec2": _destroy_ec2,
    "iam": _destroy_iam,
    "cloudwatch": _destroy_cloudwatch,
}


def _aws_err(exc: ClientError) -> str:
    err = exc.response.get("Error", {})
    return f"AWS {err.get('Code', 'ClientError')}: {err.get('Message', str(exc))}"


def plan_composed(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    enabled = enabled_modules(config)
    order = [m for m in APPLY_ORDER if m in enabled]
    all_lines: list[str] = ["Plan (boto3 — direct AWS SDK):", ""]
    all_resources: list[str] = []
    for mod in order:
        result = _PLAN_HANDLERS[mod](config, aws_creds, region)
        if result.get("error"):
            return {
                "success": False,
                "output": "",
                "error": result["error"],
                "has_changes": False,
                "resources": [],
            }
        all_lines.extend(result.get("lines") or [])
        all_resources.extend(result.get("resources") or [])
    all_lines.extend(["", f"Plan: {len(all_resources)} resource(s) to add.", "", "✓ Ready to apply."])
    return {
        "success": True,
        "output": "\n".join(all_lines),
        "error": None,
        "has_changes": bool(all_resources),
        "resources": all_resources,
    }


def apply_composed(
    config: dict,
    aws_creds: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext.from_dict(existing_ctx)
    enabled = enabled_modules(config)
    order = [m for m in APPLY_ORDER if m in enabled]
    steps: list[str] = []
    for mod in order:
        result = _APPLY_HANDLERS[mod](config, aws_creds, region, ctx)
        steps.extend(result.get("steps") or [])
        if not result.get("success"):
            return {
                "success": False,
                "output": "\n".join(steps),
                "error": result.get("error"),
                "resources": [],
                "boto3_context": ctx.to_dict(),
            }
    steps.append("")
    steps.append("Deployment complete (boto3).")
    return {
        "success": True,
        "output": "\n".join(steps),
        "error": None,
        "resources": [],
        "boto3_context": ctx.to_dict(),
    }


def destroy_composed(
    config: dict,
    aws_creds: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext.from_dict(existing_ctx)
    enabled = enabled_modules(config)
    order = [m for m in DESTROY_ORDER if m in enabled]
    steps: list[str] = []
    for mod in order:
        result = _DESTROY_HANDLERS[mod](config, aws_creds, region, ctx)
        steps.extend(result.get("steps") or [])
        if not result.get("success"):
            return {"success": False, "output": "\n".join(steps), "error": result.get("error")}
    return {"success": True, "output": "\n".join(steps), "error": None}


# Backward-compatible aliases used by routes / boto3_deployer
def plan_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    return plan_composed(config, aws_creds)


def apply_fast(config: dict, aws_creds: dict[str, str], existing_ctx: Optional[dict] = None) -> dict[str, Any]:
    return apply_composed(config, aws_creds, existing_ctx)


def destroy_fast(
    config: dict,
    aws_creds: dict[str, str],
    existing_ctx: Optional[dict] = None,
) -> dict[str, Any]:
    return destroy_composed(config, aws_creds, existing_ctx)
