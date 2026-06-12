from __future__ import annotations

import ipaddress
from typing import Optional

import boto3
from botocore.exceptions import ClientError


def client(service: str, aws_creds: dict[str, str], region: Optional[str] = None):
    region = region or aws_creds.get("AWS_DEFAULT_REGION") or "ap-south-1"
    return boto3.client(
        service,
        aws_access_key_id=aws_creds.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=aws_creds.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=aws_creds.get("AWS_SESSION_TOKEN") or None,
        region_name=region,
    )


# EC2 capacity / AZ errors that warrant retrying another subnet or instance type.
EC2_CAPACITY_ERROR_CODES = frozenset({
    "InsufficientInstanceCapacity",
    "InsufficientCapacityException",
    "InstanceTypeZoneUnsupported",
})

# Free-tier-safe fallbacks (aligned with policy-engine rules.yaml).
# CIDR slot 2 reserved for optional private subnet; public subnets use odd offsets.
PUBLIC_SUBNET_CIDR_SLOTS = (1, 3, 5, 7, 9)
MAX_PUBLIC_AZS = 3

EC2_INSTANCE_TYPE_FALLBACKS: dict[str, list[str]] = {
    "t2.micro": ["t3.micro", "t3a.micro", "t4g.micro"],
    "t3.micro": ["t3a.micro", "t4g.micro", "t2.micro"],
    "t3a.micro": ["t3.micro", "t4g.micro", "t2.micro"],
    "t4g.micro": ["t3a.micro", "t3.micro", "t2.micro"],
}


def is_ec2_capacity_error(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code", "")
    return code in EC2_CAPACITY_ERROR_CODES


def ec2_instance_types_to_try(primary: str) -> list[str]:
    """Preferred type first, then free-tier fallbacks without duplicates."""
    ordered = [primary or "t2.micro"]
    ordered.extend(EC2_INSTANCE_TYPE_FALLBACKS.get(ordered[0], []))
    seen: set[str] = set()
    out: list[str] = []
    for itype in ordered:
        if itype not in seen:
            seen.add(itype)
            out.append(itype)
    return out


def aws_err(exc: ClientError) -> str:
    err = exc.response.get("Error", {})
    code = err.get("Code", "ClientError")
    msg = err.get("Message", str(exc))
    if code in ("AccessDenied", "AccessDeniedException"):
        return (
            f"AWS {code}: {msg}. "
            "Your BYOC IAM user may lack permission for this action (e.g. budgets:* for billing)."
        )
    return f"AWS {code}: {msg}"


def cidr_subnet(base_cidr: str, new_bits: int, netnum: int) -> str:
    network = ipaddress.ip_network(base_cidr, strict=False)
    subnets = list(network.subnets(new_prefix=network.prefixlen + new_bits))
    return str(subnets[netnum])


def merge_name_tag(tags: dict, name: str) -> list[dict[str, str]]:
    tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
    if not any(t["Key"] == "Name" for t in tag_list):
        tag_list.append({"Key": "Name", "Value": name})
    return tag_list
