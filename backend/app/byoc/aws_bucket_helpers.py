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


def sanitize_username_for_bucket(username: str) -> str:
    safe = re.sub(r"[^a-z0-9-]", "-", username.lower())
    safe = re.sub(r"-+", "-", safe).strip("-")
    return (safe[:20] or "user")


def suggest_aws_bucket_names(username: str) -> Dict[str, str]:
    """Globally unique-ish suggested names (user must still create buckets in AWS)."""
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
    Returns: available | accessible | forbidden | invalid
    - available: 404 (no bucket in this account/region — name may be free to create)
    - accessible: 200 (bucket exists and keys can access it)
    - forbidden: 403 or other
    """
    fmt_err = validate_bucket_name_format(bucket_name)
    if fmt_err:
        return "invalid"

    client = _s3_client_from_keys(
        access_key_id, secret_access_key, region, session_token
    )
    try:
        client.head_bucket(Bucket=bucket_name)
        return "accessible"
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NotFound"):
            return "available"
        if code in ("403", "AccessDenied"):
            return "forbidden"
        return "forbidden"
    except Exception:
        return "forbidden"


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
            if status == "available":
                return (
                    False,
                    f"Bucket '{bucket_name}' was not found in {region}. "
                    "Create it in AWS first, then connect.",
                )
            if status == "invalid":
                return False, f"Invalid bucket name: '{bucket_name}'."
            return (
                False,
                f"Cannot access bucket '{bucket_name}' in {region}. Check name and IAM policy.",
            )
    return True, "All buckets verified."
