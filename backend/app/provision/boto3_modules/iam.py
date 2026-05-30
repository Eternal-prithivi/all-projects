from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import aws_err, client
from app.provision.boto3_modules.context import DeployContext


def plan_iam(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    role = config.get("role_name", "app-role")
    return {
        "lines": [
            f"  + aws_iam_role.main ({role})",
            "  + aws_iam_role_policy.main",
            "  + aws_iam_instance_profile.main",
        ],
        "error": None,
        "resources": [f"aws_iam_role.main:{role}"],
    }


def apply_iam(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    iam = client("iam", aws_creds, region)
    role_name = config.get("role_name", "app-role")
    profile_name = f"{role_name}-profile"
    bucket = (config.get("bucket_name") or "").strip()
    if bucket:
        resource_arn = f"arn:aws:s3:::{bucket}/*"
    else:
        resource_arn = "arn:aws:s3:::*/*"
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
                "Resource": resource_arn,
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
        iam.create_instance_profile(InstanceProfileName=profile_name)
        iam.add_role_to_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name,
        )
        ctx.instance_profile_name = profile_name
        return {
            "success": True,
            "steps": [f"✓ IAM role '{role_name}'", f"✓ Instance profile '{profile_name}'"],
            "error": None,
        }
    except ClientError as exc:
        return {"success": False, "steps": [], "error": aws_err(exc)}


def destroy_iam(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    iam = client("iam", aws_creds, region)
    role_name = config.get("role_name", "app-role")
    profile_name = ctx.instance_profile_name or f"{role_name}-profile"
    steps: list[str] = []
    try:
        try:
            iam.remove_role_from_instance_profile(
                InstanceProfileName=profile_name,
                RoleName=role_name,
            )
        except ClientError:
            pass
        try:
            iam.delete_instance_profile(InstanceProfileName=profile_name)
            steps.append(f"✓ Deleted instance profile '{profile_name}'")
        except ClientError:
            pass
        try:
            iam.delete_role_policy(RoleName=role_name, PolicyName=f"{role_name}-policy")
        except ClientError:
            pass
        iam.delete_role(RoleName=role_name)
        steps.append(f"✓ Deleted IAM role '{role_name}'")
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": aws_err(exc)}
