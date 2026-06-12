from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import (
    MAX_PUBLIC_AZS,
    PUBLIC_SUBNET_CIDR_SLOTS,
    aws_err,
    cidr_subnet,
    client,
)
from app.provision.boto3_modules.context import DeployContext


def plan_vpc(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    cidr = config.get("vpc_cidr", "10.0.0.0/16")
    lines = [
        f"  + aws_vpc.main ({cidr})",
        "  + aws_subnet.public (MapPublicIpOnLaunch=true)",
        "  + aws_subnet.private",
        "  + aws_internet_gateway.main",
        "  + aws_route_table.public",
        "  + aws_route_table_association.public",
    ]
    return {"lines": lines, "error": None, "resources": ["aws_vpc.main"]}


def apply_vpc(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    ec2 = client("ec2", aws_creds, region)
    cidr = config.get("vpc_cidr", "10.0.0.0/16")
    tags = config.get("tags") or {}
    tag_specs = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
    try:
        vpc = ec2.create_vpc(CidrBlock=cidr)
        vpc_id = vpc["Vpc"]["VpcId"]
        if tag_specs:
            ec2.create_tags(Resources=[vpc_id], Tags=tag_specs + [{"Key": "Name", "Value": "main-vpc"}])
        else:
            ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": "main-vpc"}])
        ctx.vpc_id = vpc_id

        azs = ec2.describe_availability_zones(Filters=[{"Name": "state", "Values": ["available"]}])
        names = [z["ZoneName"] for z in azs.get("AvailabilityZones", [])]
        if not names:
            names = [f"{region}a", f"{region}b"]

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

        public_subnet_ids: list[str] = []
        for i, az in enumerate(names[:MAX_PUBLIC_AZS]):
            slot = PUBLIC_SUBNET_CIDR_SLOTS[i]
            pub = ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=cidr_subnet(cidr, 8, slot),
                AvailabilityZone=az,
                TagSpecifications=[
                    {
                        "ResourceType": "subnet",
                        "Tags": [{"Key": "Name", "Value": f"public-subnet-{az}"}],
                    }
                ],
            )
            subnet_id = pub["Subnet"]["SubnetId"]
            public_subnet_ids.append(subnet_id)
            ec2.modify_subnet_attribute(
                SubnetId=subnet_id,
                MapPublicIpOnLaunch={"Value": True},
            )
            ec2.associate_route_table(RouteTableId=rt_id, SubnetId=subnet_id)

        ctx.public_subnet_ids = public_subnet_ids
        ctx.subnet_id = public_subnet_ids[0] if public_subnet_ids else None

        priv_az = names[1] if len(names) > 1 else names[0]
        ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=cidr_subnet(cidr, 8, 2),
            AvailabilityZone=priv_az,
            TagSpecifications=[{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": "private-subnet"}]}],
        )

        az_note = ", ".join(names[:MAX_PUBLIC_AZS])
        return {
            "success": True,
            "steps": [f"✓ VPC {vpc_id} + public subnets ({az_note}) + IGW"],
            "error": None,
        }
    except ClientError as exc:
        return {"success": False, "steps": [], "error": aws_err(exc)}


def destroy_vpc(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    if not ctx.vpc_id:
        return {"success": True, "steps": ["VPC: nothing to delete"], "error": None}
    ec2 = client("ec2", aws_creds, region)
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
        return {"success": False, "steps": [], "error": aws_err(exc)}
