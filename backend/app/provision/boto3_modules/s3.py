from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import aws_err, client, merge_name_tag
from app.provision.boto3_modules.context import DeployContext


def plan_s3(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    if not bucket:
        return {"lines": [], "error": "Bucket name is required for S3.", "resources": []}
    s3 = client("s3", aws_creds, region)
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


def apply_s3(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or "").strip()
    s3 = client("s3", aws_creds, region)
    steps: list[str] = []
    tags = config.get("tags") or {}
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
        if tags or bucket:
            try:
                s3.put_bucket_tagging(
                    Bucket=bucket,
                    Tagging={"TagSet": merge_name_tag(tags, bucket)},
                )
            except ClientError:
                pass
        ctx.bucket_name = bucket
        steps.append(f"✓ S3 bucket '{bucket}'")
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": aws_err(exc)}


def destroy_s3(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    bucket = (config.get("bucket_name") or ctx.bucket_name or "").strip()
    if not bucket:
        return {"success": True, "steps": ["S3: nothing to delete"], "error": None}
    s3 = client("s3", aws_creds, region)
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
        return {"success": False, "steps": [], "error": aws_err(exc)}
