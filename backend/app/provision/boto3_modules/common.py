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
