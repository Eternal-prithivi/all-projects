# =============================================================================
# MODULE: provision/boto3_deployer.py
# PURPOSE: Direct AWS SDK deploys that bypass Terraform — required because
#          Render free tier (0.1 CPU / 512MB RAM) cannot reliably run
#          `terraform plan` with the AWS provider (OOM kills, multi-minute hangs).
# USED BY: routes_provision.py for simple templates (static-site, serverless-db).
# DEPENDS ON: boto3, BYOC credentials (env-style dict from byoc_credentials).
# DO NOT:
#   - Use this for templates that need EC2/VPC — Terraform handles those.
#   - Swallow ClientError silently; user must see a clear AWS message.
# =============================================================================
from __future__ import annotations

import logging
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Templates handled directly via boto3 (fast path; no terraform).
FAST_PATH_TEMPLATES = {"static-site", "serverless-db"}


def is_fast_path_config(config: dict) -> bool:
    """True when the config matches a template we can deploy via boto3 only."""
    template = (config.get("template") or "").lower()
    if template not in FAST_PATH_TEMPLATES:
        return False
    if template == "static-site":
        return bool(config.get("enable_s3")) and not any(
            config.get(f) for f in ("enable_ec2", "enable_vpc", "enable_dynamodb")
        )
    if template == "serverless-db":
        return bool(config.get("enable_dynamodb")) and not any(
            config.get(f) for f in ("enable_ec2", "enable_vpc", "enable_s3")
        )
    return False


def _client(service: str, aws_creds: dict[str, str], region: Optional[str] = None):
    region = region or aws_creds.get("AWS_DEFAULT_REGION") or "ap-south-1"
    return boto3.client(
        service,
        aws_access_key_id=aws_creds.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=aws_creds.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=aws_creds.get("AWS_SESSION_TOKEN") or None,
        region_name=region,
    )


# ─────────────────────── PLAN (no AWS writes) ───────────────────────


def plan_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    """
    Validate the config and describe what would be created.

    Returns a fake terraform-plan-like output for the UI so users see the
    same review screen as the terraform flow.
    """
    template = (config.get("template") or "").lower()
    region = config.get("aws_region") or "ap-south-1"

    if template == "static-site":
        return _plan_static_site(config, aws_creds, region)
    if template == "serverless-db":
        return _plan_serverless_db(config, aws_creds, region)
    return {
        "success": False,
        "output": "",
        "error": f"Fast-path planning not supported for template '{template}'.",
        "resources": [],
    }


def _plan_static_site(config: dict, aws_creds: dict[str, str], region: str) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    if not bucket:
        return {
            "success": False,
            "output": "",
            "error": "Bucket name is required for Static Website.",
            "resources": [],
        }

    s3 = _client("s3", aws_creds, region)
    try:
        s3.head_bucket(Bucket=bucket)
        # Bucket exists in your account already
        return {
            "success": False,
            "output": "",
            "error": (
                f"S3 bucket '{bucket}' already exists in your AWS account. "
                "Pick a different name or destroy the existing deployment first."
            ),
            "resources": [],
        }
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            pass  # name is free — good
        elif code in ("403", "Forbidden"):
            return {
                "success": False,
                "output": "",
                "error": (
                    f"S3 bucket name '{bucket}' is taken by another AWS account. "
                    "Bucket names are globally unique — pick a different name."
                ),
                "resources": [],
            }
        elif code in ("301", "PermanentRedirect"):
            return {
                "success": False,
                "output": "",
                "error": (
                    f"Bucket '{bucket}' exists in a different region. Pick a different name."
                ),
                "resources": [],
            }
        else:
            return {
                "success": False,
                "output": "",
                "error": f"AWS error checking bucket '{bucket}': {exc}",
                "resources": [],
            }

    output = "\n".join([
        "Plan (boto3 fast path — Static Website):",
        "",
        f"  + aws_s3_bucket.main                         ({bucket}, region={region})",
        f"  + aws_s3_bucket_public_access_block.main     (block all public access)",
        f"  + aws_s3_bucket_server_side_encryption.main  (AES256)",
        f"  + aws_s3_bucket_versioning.main              (Enabled)",
        "",
        "Plan: 4 to add, 0 to change, 0 to destroy.",
        "",
        "✓ Ready to apply. Click Apply to create these resources.",
    ])
    return {
        "success": True,
        "output": output,
        "error": None,
        "has_changes": True,
        "resources": [
            f"aws_s3_bucket.main:{bucket}",
            "aws_s3_bucket_public_access_block.main",
            "aws_s3_bucket_server_side_encryption_configuration.main",
            "aws_s3_bucket_versioning.main",
        ],
    }


def _plan_serverless_db(config: dict, aws_creds: dict[str, str], region: str) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    if not table:
        return {
            "success": False, "output": "", "resources": [],
            "error": "DynamoDB table name is required.",
        }

    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.describe_table(TableName=table)
        return {
            "success": False, "output": "", "resources": [],
            "error": f"DynamoDB table '{table}' already exists. Pick a different name.",
        }
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code != "ResourceNotFoundException":
            return {
                "success": False, "output": "", "resources": [],
                "error": f"AWS error checking DynamoDB table: {exc}",
            }

    hash_key = config.get("dynamodb_hash_key", "id")
    rcu = int(config.get("dynamodb_read_capacity", 5))
    wcu = int(config.get("dynamodb_write_capacity", 5))
    output = "\n".join([
        "Plan (boto3 fast path — Serverless DB):",
        "",
        f"  + aws_dynamodb_table.main  ({table}, hash_key={hash_key}, RCU={rcu}, WCU={wcu})",
        "",
        "Plan: 1 to add, 0 to change, 0 to destroy.",
    ])
    return {
        "success": True, "output": output, "error": None, "has_changes": True,
        "resources": [f"aws_dynamodb_table.main:{table}"],
    }


# ─────────────────────── APPLY (real AWS writes) ───────────────────────


def apply_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    template = (config.get("template") or "").lower()
    region = config.get("aws_region") or "ap-south-1"

    if template == "static-site":
        return _apply_static_site(config, aws_creds, region)
    if template == "serverless-db":
        return _apply_serverless_db(config, aws_creds, region)
    return {
        "success": False,
        "output": "",
        "error": f"Fast-path apply not supported for template '{template}'.",
        "resources": [],
    }


def _apply_static_site(config: dict, aws_creds: dict[str, str], region: str) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    s3 = _client("s3", aws_creds, region)
    steps: list[str] = []

    try:
        # 1. Create bucket — special-cased for us-east-1
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        steps.append(f"✓ Created S3 bucket '{bucket}' in {region}")

        # 2. Block all public access
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        steps.append("✓ Blocked all public access")

        # 3. Enable AES256 server-side encryption
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        )
        steps.append("✓ Enabled AES256 encryption")

        # 4. Enable versioning
        s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        steps.append("✓ Enabled bucket versioning")

        # 5. Apply tags (best-effort)
        tags = config.get("tags") or {}
        if tags:
            try:
                s3.put_bucket_tagging(
                    Bucket=bucket,
                    Tagging={"TagSet": [{"Key": k, "Value": str(v)} for k, v in tags.items()]},
                )
                steps.append(f"✓ Applied {len(tags)} tag(s)")
            except ClientError as exc:
                steps.append(f"⚠ Tagging skipped: {exc.response.get('Error', {}).get('Code', '')}")

        steps.append("")
        steps.append(f"Deployment complete. 4 resources created on bucket '{bucket}'.")
        return {
            "success": True,
            "output": "\n".join(steps),
            "error": None,
            "resources": [
                f"aws_s3_bucket.main:{bucket}",
                "aws_s3_bucket_public_access_block.main",
                "aws_s3_bucket_server_side_encryption_configuration.main",
                "aws_s3_bucket_versioning.main",
            ],
        }
    except ClientError as exc:
        err_code = exc.response.get("Error", {}).get("Code", "ClientError")
        err_msg = exc.response.get("Error", {}).get("Message", str(exc))
        logger.exception("boto3 static-site apply failed: %s", err_code)
        return {
            "success": False,
            "output": "\n".join(steps),
            "error": f"AWS {err_code}: {err_msg}",
            "resources": [],
        }


def _apply_serverless_db(config: dict, aws_creds: dict[str, str], region: str) -> dict[str, Any]:
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
            "output": f"✓ Created DynamoDB table '{table}' in {region}\nRCU={rcu}, WCU={wcu}",
            "error": None,
            "resources": [f"aws_dynamodb_table.main:{table}"],
        }
    except ClientError as exc:
        err_code = exc.response.get("Error", {}).get("Code", "ClientError")
        err_msg = exc.response.get("Error", {}).get("Message", str(exc))
        return {
            "success": False,
            "output": "",
            "error": f"AWS {err_code}: {err_msg}",
            "resources": [],
        }


# ─────────────────────── DESTROY ───────────────────────


def destroy_fast(config: dict, aws_creds: dict[str, str]) -> dict[str, Any]:
    template = (config.get("template") or "").lower()
    region = config.get("aws_region") or "ap-south-1"

    if template == "static-site":
        return _destroy_static_site(config, aws_creds, region)
    if template == "serverless-db":
        return _destroy_serverless_db(config, aws_creds, region)
    return {
        "success": False,
        "output": "",
        "error": f"Fast-path destroy not supported for template '{template}'.",
    }


def _destroy_static_site(config: dict, aws_creds: dict[str, str], region: str) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    s3 = _client("s3", aws_creds, region)
    try:
        # Empty bucket (versions + delete markers) before delete — required for versioned buckets
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
        return {"success": True, "output": f"✓ Deleted S3 bucket '{bucket}'", "error": None}
    except ClientError as exc:
        err_code = exc.response.get("Error", {}).get("Code", "ClientError")
        err_msg = exc.response.get("Error", {}).get("Message", str(exc))
        return {"success": False, "output": "", "error": f"AWS {err_code}: {err_msg}"}


def _destroy_serverless_db(config: dict, aws_creds: dict[str, str], region: str) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.delete_table(TableName=table)
        return {"success": True, "output": f"✓ Deleted DynamoDB table '{table}'", "error": None}
    except ClientError as exc:
        err_code = exc.response.get("Error", {}).get("Code", "ClientError")
        err_msg = exc.response.get("Error", {}).get("Message", str(exc))
        return {"success": False, "output": "", "error": f"AWS {err_code}: {err_msg}"}
