# =============================================================================
# MODULE: provision/boto3_drift.py
# PURPOSE: Drift detection for boto3 deployments — compare Mongo config vs live AWS.
# No Terraform workspace required (works on localhost and Render).
# =============================================================================
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from botocore.exceptions import ClientError

from app.provision.boto3_composer import DeployContext, _client
from app.provision.models import DriftReport, DriftStatus

logger = logging.getLogger(__name__)


def detect_drift_boto3(
    config: dict,
    aws_creds: dict[str, str],
    boto3_context: Optional[dict] = None,
) -> DriftReport:
    """Compare desired config to live AWS for enabled modules."""
    region = config.get("aws_region") or "ap-south-1"
    ctx = DeployContext.from_dict(boto3_context)
    details: list[str] = []
    changes = 0

    try:
        if config.get("enable_s3"):
            c, d = _check_s3(config, aws_creds, region)
            changes += c
            details.extend(d)

        if config.get("enable_dynamodb"):
            c, d = _check_dynamodb(config, aws_creds, region)
            changes += c
            details.extend(d)

        if config.get("enable_ec2") and ctx.instance_id:
            c, d = _check_ec2(config, aws_creds, region, ctx.instance_id)
            changes += c
            details.extend(d)

        if config.get("enable_cloudwatch") and ctx.sns_topic_arn:
            c, d = _check_cloudwatch(config, aws_creds, region, ctx)
            changes += c
            details.extend(d)

        if changes > 0:
            return DriftReport(
                status=DriftStatus.DRIFT_DETECTED,
                changes_detected=changes,
                details=details[:20],
                checked_at=datetime.utcnow(),
            )
        return DriftReport(
            status=DriftStatus.CLEAN,
            changes_detected=0,
            details=["Infrastructure matches saved configuration — no drift detected (boto3)."],
            checked_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("boto3 drift check failed")
        return DriftReport(
            status=DriftStatus.CHECK_FAILED,
            changes_detected=0,
            details=[str(exc)],
            checked_at=datetime.utcnow(),
        )


def remediate_drift_boto3(
    config: dict,
    aws_creds: dict[str, str],
    boto3_context: Optional[dict] = None,
    check_only: bool = True,
) -> dict[str, Any]:
    """Re-apply boto3 modules to restore desired state (or dry-run message)."""
    from app.provision.boto3_composer import apply_composed

    if check_only:
        report = detect_drift_boto3(config, aws_creds, boto3_context)
        if report.status == DriftStatus.CLEAN:
            return {
                "success": True,
                "performed": False,
                "message": "No drift detected — infrastructure matches desired state.",
                "plan_output": "\n".join(report.details),
            }
        return {
            "success": True,
            "performed": False,
            "message": "Drift detected. Set check_only=false to re-apply boto3 configuration.",
            "plan_output": "\n".join(report.details),
        }

    result = apply_composed(config, aws_creds, boto3_context)
    return {
        "success": result.get("success", False),
        "performed": True,
        "message": "Boto3 re-apply finished." if result.get("success") else result.get("error"),
        "plan_output": result.get("output", ""),
        "apply_output": result.get("output", ""),
        "boto3_context": result.get("boto3_context"),
    }


def _check_s3(config: dict, aws_creds: dict, region: str) -> tuple[int, list[str]]:
    bucket = (config.get("bucket_name") or "").strip()
    if not bucket:
        return 0, []
    s3 = _client("s3", aws_creds, region)
    details: list[str] = []
    changes = 0
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        details.append(f"~ S3 bucket '{bucket}' missing or inaccessible")
        return 1, details

    try:
        enc = s3.get_bucket_encryption(Bucket=bucket)
        algo = (
            enc.get("ServerSideEncryptionConfiguration", {})
            .get("Rules", [{}])[0]
            .get("ApplyServerSideEncryptionByDefault", {})
            .get("SSEAlgorithm")
        )
        if algo != "AES256":
            changes += 1
            details.append(f"~ S3 encryption is {algo}, expected AES256")
    except ClientError:
        changes += 1
        details.append("~ S3 encryption not configured (expected AES256)")

    try:
        ver = s3.get_bucket_versioning(Bucket=bucket)
        if ver.get("Status") != "Enabled":
            changes += 1
            details.append("~ S3 versioning not enabled")
    except ClientError:
        changes += 1
        details.append("~ Could not read S3 versioning")

    try:
        pab = s3.get_public_access_block(Bucket=bucket)
        cfg = pab.get("PublicAccessBlockConfiguration", {})
        if not all(cfg.get(k) for k in ("BlockPublicAcls", "BlockPublicPolicy", "IgnorePublicAcls", "RestrictPublicBuckets")):
            changes += 1
            details.append("~ S3 public access block does not match policy")
    except ClientError:
        changes += 1
        details.append("~ S3 public access block missing")

    return changes, details


def _check_dynamodb(config: dict, aws_creds: dict, region: str) -> tuple[int, list[str]]:
    table = (config.get("dynamodb_table_name") or "").strip()
    if not table:
        return 0, []
    ddb = _client("dynamodb", aws_creds, region)
    try:
        ddb.describe_table(TableName=table)
        return 0, []
    except ClientError:
        return 1, [f"~ DynamoDB table '{table}' missing"]


def _check_ec2(config: dict, aws_creds: dict, region: str, instance_id: str) -> tuple[int, list[str]]:
    ec2 = _client("ec2", aws_creds, region)
    try:
        res = ec2.describe_instances(InstanceIds=[instance_id])
        state = res["Reservations"][0]["Instances"][0]["State"]["Name"]
        if state not in ("running", "pending"):
            return 1, [f"~ EC2 instance {instance_id} state is {state}"]
        return 0, []
    except ClientError:
        return 1, [f"~ EC2 instance {instance_id} not found"]


def _check_cloudwatch(
    config: dict, aws_creds: dict, region: str, ctx: DeployContext
) -> tuple[int, list[str]]:
    if not ctx.sns_topic_arn:
        return 0, []
    sns = _client("sns", aws_creds, region)
    try:
        sns.get_topic_attributes(TopicArn=ctx.sns_topic_arn)
        return 0, []
    except ClientError:
        return 1, ["~ SNS alerts topic missing"]
