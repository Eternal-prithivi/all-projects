"""AWS BYOC bucket naming, validation, and access checks."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.utils.config import settings

S3_CONFIG = Config(signature_version="s3v4")
REPLICA_REGION_DEFAULT = "us-east-1"
BUCKET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


def resolve_bucket_target_region(
    bucket_role: str,
    requested_region: Optional[str],
    primary_region: str = "ap-south-1",
) -> str:
    """Replica buckets are always created in us-east-1 (N. Virginia)."""
    if (bucket_role or "").lower() == "replica":
        return REPLICA_REGION_DEFAULT
    return (requested_region or primary_region or "ap-south-1").strip()


def normalize_s3_location_constraint(location_constraint: Optional[str]) -> str:
    """Map GetBucketLocation response to a region code."""
    if not location_constraint:
        return "us-east-1"
    return location_constraint


def get_bucket_actual_region(
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    session_token: Optional[str] = None,
) -> Optional[str]:
    """Return the AWS region where the bucket actually lives."""
    client = _s3_client_from_keys(
        access_key_id, secret_access_key, "us-east-1", session_token
    )
    try:
        loc = client.get_bucket_location(Bucket=bucket_name).get("LocationConstraint")
        return normalize_s3_location_constraint(loc)
    except ClientError:
        return None


def sanitize_username_for_bucket(username: str) -> str:
    safe = re.sub(r"[^a-z0-9-]", "-", username.lower())
    safe = re.sub(r"-+", "-", safe).strip("-")
    return (safe[:20] or "user")


def suggest_aws_bucket_names(username: str) -> Dict[str, str]:
    """Globally unique-ish suggested names (Zenith can create these on connect)."""
    suffix = uuid.uuid4().hex[:6]
    base = sanitize_username_for_bucket(username)
    return {
        "storage_bucket_name": f"zenith-{base}-{suffix}-storage",
        "secure_bucket_name": f"zenith-{base}-{suffix}-secure",
        "replica_bucket_name": f"zenith-{base}-{suffix}-replica",
    }


def validate_bucket_name_format(name: str) -> Optional[str]:
    if not name or len(name) < 3 or len(name) > 63:
        return "Bucket name must be 3–63 characters."
    if not BUCKET_NAME_RE.match(name):
        return "Use lowercase letters, numbers, dots, and hyphens only."
    if ".." in name or name.startswith(".") or name.endswith("."):
        return "Bucket name cannot start or end with a dot or contain '..'"
    return None


def _s3_client_from_keys(
    access_key_id: str,
    secret_access_key: str,
    region: str,
    session_token: Optional[str] = None,
):
    kwargs: dict = {
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
        "region_name": region,
        "config": S3_CONFIG,
    }
    if session_token:
        kwargs["aws_session_token"] = session_token
    return boto3.client("s3", **kwargs)


def verify_aws_access_keys(
    access_key_id: str, secret_access_key: str, region: str = "ap-south-1"
) -> Tuple[bool, str, Optional[str]]:
    """Validate keys via STS GetCallerIdentity."""
    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        ident = sts.get_caller_identity()
        account = ident.get("Account")
        return True, "Credentials verified.", account
    except Exception as e:
        return False, f"Invalid credentials: {str(e)[:120]}", None


def assume_role_temp_credentials(
    role_arn: str, external_id: str, region: str = "ap-south-1"
) -> Tuple[bool, str, Optional[dict]]:
    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=region,
        )
        assumed = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="ZenithBYOCVerify",
            ExternalId=external_id,
            DurationSeconds=900,
        )
        creds = assumed["Credentials"]
        return True, "IAM role verified.", {
            "access_key_id": creds["AccessKeyId"],
            "secret_access_key": creds["SecretAccessKey"],
            "session_token": creds["SessionToken"],
        }
    except Exception as e:
        return False, f"Role assumption failed: {str(e)[:120]}", None


def check_bucket_access(
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    region: str,
    session_token: Optional[str] = None,
) -> str:
    """
    Returns: available | accessible | forbidden | invalid | wrong_region
    - accessible: bucket exists in the expected region
    - wrong_region: bucket exists but not in `region` (common when replica should be us-east-1)
    """
    fmt_err = validate_bucket_name_format(bucket_name)
    if fmt_err:
        return "invalid"

    client = _s3_client_from_keys(
        access_key_id, secret_access_key, region, session_token
    )
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NotFound"):
            return "available"
        if code in ("403", "AccessDenied"):
            return "forbidden"
        if code in ("301", "PermanentRedirect"):
            actual = get_bucket_actual_region(
                access_key_id, secret_access_key, bucket_name, session_token
            )
            if actual and actual != region:
                return "wrong_region"
        return "forbidden"
    except Exception:
        return "forbidden"

    actual = get_bucket_actual_region(
        access_key_id, secret_access_key, bucket_name, session_token
    )
    if actual and actual != region:
        return "wrong_region"
    return "accessible"


def _apply_bucket_baseline(
    client,
    bucket_name: str,
) -> None:
    """Match provision Terraform S3 module: block public access, AES256, versioning."""
    client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    client.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                }
            ]
        },
    )
    client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"},
    )


def create_s3_bucket(
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    region: str,
    session_token: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Create bucket in the user's account with baseline security settings.
    Returns (success, message). Idempotent if bucket already exists and is accessible.
    """
    fmt_err = validate_bucket_name_format(bucket_name)
    if fmt_err:
        return False, fmt_err

    status = check_bucket_access(
        access_key_id, secret_access_key, bucket_name, region, session_token
    )
    if status == "accessible":
        return True, "Bucket already exists."
    if status == "forbidden":
        return (
            False,
            f"Cannot create '{bucket_name}': access denied or name taken globally.",
        )

    client = _s3_client_from_keys(
        access_key_id, secret_access_key, region, session_token
    )
    try:
        if region == "us-east-1":
            client.create_bucket(Bucket=bucket_name)
        else:
            client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("BucketAlreadyOwnedByYou",):
            pass
        elif code in ("BucketAlreadyExists",):
            return (
                False,
                f"Bucket name '{bucket_name}' is already taken by another AWS account.",
            )
        else:
            return False, f"CreateBucket failed: {str(e)[:160]}"

    try:
        _apply_bucket_baseline(client, bucket_name)
    except ClientError as e:
        return (
            False,
            f"Bucket '{bucket_name}' was created but securing it failed: {str(e)[:120]}. "
            "Add s3:PutBucketPublicAccessBlock, PutEncryptionConfiguration, PutBucketVersioning to IAM.",
        )

    actual = get_bucket_actual_region(
        access_key_id, secret_access_key, bucket_name, session_token
    )
    if actual and actual != region:
        return (
            False,
            f"Bucket '{bucket_name}' exists in {actual} but must be in {region}. "
            "Delete the bucket in AWS and try again.",
        )
    verify = check_bucket_access(
        access_key_id, secret_access_key, bucket_name, region, session_token
    )
    if verify != "accessible":
        return False, f"Bucket '{bucket_name}' was created but is not accessible yet."
    return True, f"Bucket '{bucket_name}' created in {region}."


def ensure_aws_buckets_exist(
    access_key_id: str,
    secret_access_key: str,
    buckets: List[Tuple[str, str]],
    session_token: Optional[str] = None,
) -> Tuple[bool, str]:
    """Create any missing buckets, then verify all are accessible."""
    created: List[str] = []
    for bucket_name, region in buckets:
        status = check_bucket_access(
            access_key_id, secret_access_key, bucket_name, region, session_token
        )
        if status == "accessible":
            continue
        if status == "wrong_region":
            actual = get_bucket_actual_region(
                access_key_id, secret_access_key, bucket_name, session_token
            )
            return (
                False,
                f"Bucket '{bucket_name}' is in {actual or 'another region'}, "
                f"but must be in {region}. Delete it in AWS and reconnect.",
            )
        if status != "available":
            if status == "invalid":
                return False, f"Invalid bucket name: '{bucket_name}'."
            return (
                False,
                f"Cannot use bucket '{bucket_name}' in {region}. Check IAM permissions.",
            )
        ok, message = create_s3_bucket(
            access_key_id, secret_access_key, bucket_name, region, session_token
        )
        if not ok:
            return False, message
        created.append(bucket_name)

    ok, message = test_aws_buckets_access(
        access_key_id, secret_access_key, buckets, session_token
    )
    if not ok:
        return False, message
    if created:
        return True, f"Created {len(created)} bucket(s): {', '.join(created)}. {message}"
    return True, message


def test_aws_buckets_access(
    access_key_id: str,
    secret_access_key: str,
    buckets: List[Tuple[str, str]],
    session_token: Optional[str] = None,
) -> Tuple[bool, str]:
    """Test HeadBucket for each (bucket_name, region). All must be accessible."""
    for bucket_name, region in buckets:
        status = check_bucket_access(
            access_key_id, secret_access_key, bucket_name, region, session_token
        )
        if status != "accessible":
            if status == "wrong_region":
                actual = get_bucket_actual_region(
                    access_key_id, secret_access_key, bucket_name, session_token
                )
                return (
                    False,
                    f"Bucket '{bucket_name}' is in {actual or 'another region'}, "
                    f"not {region}. Delete it in AWS and try again.",
                )
            if status == "available":
                return (
                    False,
                    f"Bucket '{bucket_name}' was not found in {region}.",
                )
            if status == "invalid":
                return False, f"Invalid bucket name: '{bucket_name}'."
            return (
                False,
                f"Cannot access bucket '{bucket_name}' in {region}. Check name and IAM policy.",
            )
    return True, "All buckets verified."
