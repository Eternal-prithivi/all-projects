# =============================================================================
# MODULE: byoc/routes_byoc.py  (493 lines)
# PURPOSE: BYOC (Bring Your Own Cloud) credential management — connect/test/disconnect
#          user-owned AWS/GCP/Azure accounts, store encrypted credentials in DB
# READS FROM:  byoc_credentials collection, users collection (subscription_tier)
# WRITES TO:   byoc_credentials collection
# DEPENDS ON:  credential_resolver.py, auth_utils.get_current_user()
# MOUNTED AT:  /api/byoc → connect, test, status, disconnect
# DO NOT:
#   - Store plaintext cloud credentials — they must be encrypted at rest
#   - Allow BYOC for Free-tier users — check subscription_tier before accepting creds
#   - Merge BYOC and platform credentials — credential_resolver.py handles the routing
# =============================================================================
"""
Supports two methods:
  - Access Keys: User provides their cloud access keys directly
  - IAM Role: User creates a role in their account, Zenith assumes it via STS (no keys exchanged)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.auth.auth_utils import get_current_user
from app.users.user_model import User
from app.database.mongo_client import get_database
from app.byoc.encryption import encrypt_credential, encrypt_credentials_dict
from app.byoc.credential_resolver import get_aws_bucket_layout, get_byoc_status
from app.byoc.aws_bucket_helpers import (
    REPLICA_REGION_DEFAULT,
    assume_role_temp_credentials,
    check_bucket_access,
    create_s3_bucket,
    ensure_aws_buckets_exist,
    suggest_aws_bucket_names,
    test_aws_buckets_access,
    validate_bucket_name_format,
    verify_aws_access_keys,
)
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

DB = get_database()
byoc_collection = DB["byoc_credentials"]
subscriptions_collection = DB["subscriptions"]

# Zenith's AWS Account ID — needed for IAM Role trust policy
ZENITH_AWS_ACCOUNT_ID = "412628362844"

# --- IAM Policy Templates ---
IAM_POLICY_TEMPLATES = {
    "AWS": {
        "access_keys": {
            "title": "Quick Setup — Access Keys",
            "setup_steps": [
                "Go to AWS Console → IAM → Users",
                "Find your existing user (or create a new one)",
                "Go to Security credentials → Create access key",
                "Copy the Access Key ID and Secret Access Key",
                "Paste them below along with your bucket name"
            ]
        },
        "iam_role": {
            "title": "Secure Setup — IAM Role",
            "zenith_account_id": ZENITH_AWS_ACCOUNT_ID,
            "trust_policy": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": f"arn:aws:iam::{ZENITH_AWS_ACCOUNT_ID}:root"
                        },
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {
                                "sts:ExternalId": "EXTERNAL_ID_PLACEHOLDER"
                            }
                        }
                    }
                ]
            },
            "permissions_policy": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "ZenithBYOCBuckets",
                        "Effect": "Allow",
                        "Action": [
                            "s3:CreateBucket",
                            "s3:PutObject",
                            "s3:GetObject",
                            "s3:DeleteObject",
                            "s3:ListBucket",
                            "s3:GetBucketLocation",
                            "s3:PutBucketPublicAccessBlock",
                            "s3:PutEncryptionConfiguration",
                            "s3:PutBucketVersioning"
                        ],
                        "Resource": [
                            "arn:aws:s3:::YOUR_STORAGE_BUCKET",
                            "arn:aws:s3:::YOUR_STORAGE_BUCKET/*",
                            "arn:aws:s3:::YOUR_SECURE_BUCKET",
                            "arn:aws:s3:::YOUR_SECURE_BUCKET/*",
                            "arn:aws:s3:::YOUR_REPLICA_BUCKET",
                            "arn:aws:s3:::YOUR_REPLICA_BUCKET/*"
                        ]
                    }
                ]
            },
            "setup_steps": [
                "Go to AWS Console → IAM → Roles → Create Role",
                "Select 'Another AWS account' as trusted entity",
                "Enter Zenith's Account ID: {account_id}",
                "Check 'Require external ID' and enter: {external_id}",
                "Click Next → Create a policy with the permissions JSON below (replace YOUR_STORAGE_BUCKET, YOUR_SECURE_BUCKET, YOUR_REPLICA_BUCKET)",
                "Attach the policy → Name the role 'ZenithBYOC' → Create",
                "Copy the Role ARN (e.g., arn:aws:iam::123456789012:role/ZenithBYOC)",
                "Paste the Role ARN in Step 1 — Zenith will create your S3 buckets in Step 2"
            ]
        }
    },
    "GCP": {
        "access_keys": {
            "title": "Quick Setup — Service Account Key",
            "setup_steps": [
                "Go to Google Cloud Console → IAM & Admin → Service Accounts",
                "Create a new service account named 'zenith-byoc'",
                "Grant the role 'Storage Object Admin' on your bucket",
                "Create a key → Download JSON key file",
                "Copy the JSON content and paste it below"
            ]
        },
        "iam_role": {
            "title": "Secure Setup — Workload Identity Federation",
            "setup_steps": [
                "Note: For GCP, the secure method uses a Service Account with restricted permissions",
                "Go to Google Cloud Console → IAM & Admin → Service Accounts",
                "Create a new service account named 'zenith-byoc-restricted'",
                "Grant ONLY the role 'Storage Object Admin' on your specific bucket",
                "Create a key → Download JSON key file",
                "Copy the JSON content and paste it below"
            ]
        }
    },
    "Azure": {
        "access_keys": {
            "title": "Quick Setup — Account Key",
            "setup_steps": [
                "Go to Azure Portal → Storage Accounts → your account",
                "Go to Access keys → copy the Storage Account Name and Key",
                "Provide the container name you want Zenith to use"
            ]
        },
        "iam_role": {
            "title": "Secure Setup — SAS Token (Scoped)",
            "setup_steps": [
                "Go to Azure Portal → Storage Accounts → your account",
                "Go to Shared access signature (SAS)",
                "Scope permissions to: Read, Write, Delete, List on Blob service only",
                "Set expiry to your desired duration",
                "Generate the SAS token and provide it below"
            ]
        }
    }
}


# --- Pydantic Models ---

class BYOCConnectRequest(BaseModel):
    """Request to connect a BYOC cloud account."""
    csp: str = Field(..., description="Cloud provider: AWS, GCP, or Azure")
    connection_method: str = Field(..., description="'access_keys' or 'iam_role'")
    
    # AWS - Access Keys method
    access_key_id: Optional[str] = Field(None, description="AWS Access Key ID")
    secret_access_key: Optional[str] = Field(None, description="AWS Secret Access Key")
    bucket_name: Optional[str] = Field(None, description="Legacy: storage bucket name")
    storage_bucket_name: Optional[str] = Field(None, description="S3 bucket for regular storage")
    secure_bucket_name: Optional[str] = Field(None, description="S3 bucket for security vault")
    replica_bucket_name: Optional[str] = Field(None, description="S3 replica bucket (us-east-1)")
    secure_dual_write: bool = Field(True, description="Replicate secure files to replica bucket")
    region: Optional[str] = Field("ap-south-1", description="AWS primary region")
    primary_region: Optional[str] = Field(None, description="Region for storage + secure buckets")
    replica_region: Optional[str] = Field(REPLICA_REGION_DEFAULT, description="Replica region")
    
    # AWS - IAM Role method
    role_arn: Optional[str] = Field(None, description="AWS IAM Role ARN")
    external_id: Optional[str] = Field(None, description="External ID for STS AssumeRole")
    
    # GCP
    service_account_json: Optional[str] = Field(None, description="GCP service account JSON content")
    gcp_bucket_name: Optional[str] = Field(None, description="GCP bucket name")
    
    # Azure
    account_name: Optional[str] = Field(None, description="Azure storage account name")
    account_key: Optional[str] = Field(None, description="Azure storage account key")
    container_name: Optional[str] = Field(None, description="Azure container name")


class BYOCTestResult(BaseModel):
    """Result of testing BYOC credentials."""
    success: bool
    message: str
    csp: str
    bucket_name: Optional[str] = None


class BYOCVerifyCredentialsRequest(BaseModel):
    """Step 1: verify AWS credentials only (not persisted)."""
    csp: str = Field("AWS", description="Cloud provider")
    connection_method: str = Field("access_keys", description="access_keys or iam_role")
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    role_arn: Optional[str] = None
    region: Optional[str] = "ap-south-1"


class BYOCCheckBucketRequest(BaseModel):
    """Check or create a single bucket with user's credentials."""
    bucket_name: str
    region: str = "ap-south-1"
    connection_method: str = "access_keys"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    role_arn: Optional[str] = None
    session_token: Optional[str] = None
    create_if_missing: bool = False


def _resolve_aws_session_creds(
    username: str,
    connection_method: str,
    primary_region: str,
    access_key_id: Optional[str],
    secret_access_key: Optional[str],
    role_arn: Optional[str],
) -> tuple[str, str, Optional[str]]:
    """Return (access_key_id, secret_access_key, session_token) for AWS API calls."""
    method = (connection_method or "access_keys").lower()
    if method == "iam_role":
        if not role_arn:
            raise HTTPException(status_code=400, detail="role_arn is required for IAM role.")
        ext_id = get_or_create_external_id(username)
        ok, message, temp = assume_role_temp_credentials(role_arn, ext_id, primary_region)
        if not ok or not temp:
            raise HTTPException(status_code=400, detail=message)
        return (
            temp["access_key_id"],
            temp["secret_access_key"],
            temp.get("session_token"),
        )
    if not access_key_id or not secret_access_key:
        raise HTTPException(
            status_code=400,
            detail="access_key_id and secret_access_key are required.",
        )
    return access_key_id, secret_access_key, None


def _resolve_aws_storage_bucket(request: BYOCConnectRequest) -> str:
    return (
        request.storage_bucket_name
        or request.bucket_name
        or ""
    ).strip()


def _save_aws_byoc_record(
    user: User,
    request: BYOCConnectRequest,
    credentials_to_encrypt: dict,
    storage_bucket: str,
    secure_bucket: str,
    replica_bucket: str,
    primary_region: str,
    replica_region: str,
) -> None:
    encrypted_creds = encrypt_credentials_dict(credentials_to_encrypt)
    credentials_to_encrypt.setdefault("region", primary_region)

    byoc_collection.update_one(
        {"username": user.username, "csp": "AWS"},
        {
            "$set": {
                "username": user.username,
                "csp": "AWS",
                "connection_method": request.connection_method,
                "credentials": encrypted_creds,
                "bucket_name": storage_bucket,
                "storage_bucket_name": storage_bucket,
                "secure_bucket_name": secure_bucket,
                "replica_bucket_name": replica_bucket,
                "primary_region": primary_region,
                "replica_region": replica_region,
                "region": primary_region,
                "secure_dual_write": request.secure_dual_write,
                "is_active": True,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
        upsert=True,
    )


# --- Helper: Check plan eligibility ---

def check_byoc_eligibility(username: str):
    """Check if user's plan supports BYOC (Pro or Enterprise only)."""
    sub = subscriptions_collection.find_one(
        {"$or": [{"username": username}, {"user_id": username}]}
    )
    plan = sub.get("plan_id", "free") if sub else "free"
    
    if plan not in ("pro", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "BYOC is available for Pro and Enterprise plans only.",
                "current_plan": plan,
                "upgrade_required": True
            }
        )
    return plan


# --- Helper: Test credentials ---

def test_aws_access_keys(access_key_id: str, secret_access_key: str, bucket_name: str, region: str = "ap-south-1") -> BYOCTestResult:
    """Test AWS S3 credentials using access keys."""
    import boto3
    try:
        s3 = boto3.client('s3',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        s3.head_bucket(Bucket=bucket_name)
        return BYOCTestResult(success=True, message="Successfully connected to your AWS S3 bucket!", csp="AWS", bucket_name=bucket_name)
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            return BYOCTestResult(success=False, message="Access denied. Check your permissions for this bucket.", csp="AWS")
        elif "404" in error_msg:
            return BYOCTestResult(success=False, message=f"Bucket '{bucket_name}' not found. Check the bucket name.", csp="AWS")
        else:
            return BYOCTestResult(success=False, message=f"Connection failed: {error_msg[:100]}", csp="AWS")


def test_aws_iam_role(role_arn: str, external_id: str, bucket_name: str, region: str = "ap-south-1") -> BYOCTestResult:
    """Test AWS S3 access via IAM Role assumption (STS AssumeRole)."""
    import boto3
    try:
        # Use Zenith's credentials to assume the user's role
        sts = boto3.client('sts',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
        # Assume the user's role
        assumed = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="ZenithBYOCTest",
            ExternalId=external_id,
            DurationSeconds=900  # 15 minutes for testing
        )
        
        temp_creds = assumed['Credentials']
        
        # Use temporary credentials to access their bucket
        s3 = boto3.client('s3',
            aws_access_key_id=temp_creds['AccessKeyId'],
            aws_secret_access_key=temp_creds['SecretAccessKey'],
            aws_session_token=temp_creds['SessionToken'],
            region_name=region
        )
        s3.head_bucket(Bucket=bucket_name)
        
        return BYOCTestResult(
            success=True,
            message="IAM Role assumed successfully! Connected to your S3 bucket with temporary credentials.",
            csp="AWS",
            bucket_name=bucket_name
        )
    except Exception as e:
        error_msg = str(e)
        if "AccessDenied" in error_msg or "is not authorized" in error_msg:
            return BYOCTestResult(success=False, message="Cannot assume role. Check the trust policy — make sure Zenith's Account ID and External ID are correct.", csp="AWS")
        elif "Not Found" in error_msg or "NoSuchBucket" in error_msg:
            return BYOCTestResult(success=False, message=f"Role assumed successfully, but bucket '{bucket_name}' not found.", csp="AWS")
        else:
            return BYOCTestResult(success=False, message=f"Role assumption failed: {error_msg[:120]}", csp="AWS")


def test_gcp_credentials(service_account_json: str, bucket_name: str) -> BYOCTestResult:
    """Test GCP credentials by checking bucket access."""
    import json as json_module
    from google.cloud import storage as gcp_storage
    from google.oauth2 import service_account
    
    try:
        creds_dict = json_module.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = gcp_storage.Client(credentials=credentials, project=creds_dict.get("project_id"))
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            return BYOCTestResult(success=True, message="Successfully connected to your GCP bucket!", csp="GCP", bucket_name=bucket_name)
        else:
            return BYOCTestResult(success=False, message=f"Bucket '{bucket_name}' not found.", csp="GCP")
    except Exception as e:
        return BYOCTestResult(success=False, message=f"Connection failed: {str(e)[:100]}", csp="GCP")


def test_azure_credentials(account_name: str, account_key: str, container_name: str) -> BYOCTestResult:
    """Test Azure credentials by checking container access."""
    from azure.storage.blob import BlobServiceClient
    try:
        conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
        client = BlobServiceClient.from_connection_string(conn_str)
        container = client.get_container_client(container_name)
        container.get_container_properties()
        return BYOCTestResult(success=True, message="Successfully connected to your Azure container!", csp="Azure", bucket_name=container_name)
    except Exception as e:
        return BYOCTestResult(success=False, message=f"Connection failed: {str(e)[:100]}", csp="Azure")


# --- Helper: Generate External ID ---

def get_or_create_external_id(username: str) -> str:
    """Generate a unique external ID for a user's IAM Role trust policy."""
    record = byoc_collection.find_one({"username": username, "type": "external_id"})
    if record:
        return record["external_id"]
    
    ext_id = f"zenith-{username}-{uuid.uuid4().hex[:8]}"
    byoc_collection.insert_one({
        "username": username,
        "type": "external_id",
        "external_id": ext_id,
        "created_at": datetime.utcnow()
    })
    return ext_id


# --- API Routes ---

@router.get("/status", summary="Get BYOC Status")
async def get_status(user: User = Depends(get_current_user)):
    """Get BYOC connection status for all cloud providers."""
    status_data = get_byoc_status(user.username)
    
    sub = subscriptions_collection.find_one(
        {"$or": [{"username": user.username}, {"user_id": user.username}]}
    )
    plan = sub.get("plan_id", "free") if sub else "free"
    
    return {
        "eligible": plan in ("pro", "enterprise"),
        "current_plan": plan,
        "connections": status_data
    }


@router.get("/storage-targets", summary="Where Storage and Security files are stored")
async def get_storage_targets(user: User = Depends(get_current_user)):
    """Read-only destination info for Storage and Security pages."""
    layout = get_aws_bucket_layout(user.username)
    if layout:
        storage = layout["storage_bucket_name"]
        secure = layout["secure_bucket_name"]
        return {
            "mode": "byoc",
            "csp": "AWS",
            "storage": {
                "bucket": storage,
                "region": layout["primary_region"],
                "key_prefix": f"{user.username}/",
            },
            "security": {
                "bucket": secure,
                "region": layout["primary_region"],
                "key_prefix": f"{user.username}/"
                if layout.get("uses_dedicated_secure_bucket")
                else f"secure/{user.username}/",
                "replica_bucket": layout.get("replica_bucket_name") or None,
                "replica_region": layout.get("replica_region") or None,
                "secure_dual_write": layout.get("secure_dual_write", True),
            },
        }
    return {
        "mode": "platform",
        "storage": {
            "bucket": getattr(settings, "REGULAR_S3_BUCKET_NAME", settings.S3_BUCKET_NAME),
            "region": settings.PRIMARY_S3_REGION,
            "key_prefix": f"{user.username}/",
        },
        "security": {
            "bucket": settings.SECURE_S3_BUCKET_NAME,
            "region": settings.PRIMARY_S3_REGION,
            "key_prefix": f"{user.username}/",
            "replica_bucket": settings.REPLICA_S3_BUCKET_NAME,
            "replica_region": settings.REPLICA_S3_REGION,
            "secure_dual_write": True,
        },
    }


@router.post("/verify-credentials", summary="Step 1 — Verify cloud credentials only")
async def verify_credentials(
    request: BYOCVerifyCredentialsRequest,
    user: User = Depends(get_current_user),
):
    """Validate credentials without saving. Returns suggested bucket names for Step 2."""
    check_byoc_eligibility(user.username)
    csp = request.csp.upper()
    if csp != "AWS":
        raise HTTPException(status_code=400, detail="Step 1 verify is implemented for AWS only.")

    region = request.region or "ap-south-1"
    suggestions = suggest_aws_bucket_names(user.username)

    if request.connection_method == "iam_role":
        if not request.role_arn:
            raise HTTPException(status_code=400, detail="role_arn is required.")
        ext_id = get_or_create_external_id(user.username)
        ok, message, _temp = assume_role_temp_credentials(request.role_arn, ext_id, region)
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        return {
            "valid": True,
            "message": message,
            "csp": "AWS",
            "aws_account_id": None,
            "suggestions": suggestions,
            "primary_region": region,
            "replica_region": REPLICA_REGION_DEFAULT,
            "external_id": ext_id,
        }

    if not request.access_key_id or not request.secret_access_key:
        raise HTTPException(
            status_code=400,
            detail="access_key_id and secret_access_key are required.",
        )
    ok, message, account_id = verify_aws_access_keys(
        request.access_key_id, request.secret_access_key, region
    )
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {
        "valid": True,
        "message": message,
        "csp": "AWS",
        "aws_account_id": account_id,
        "suggestions": suggestions,
        "primary_region": region,
        "replica_region": REPLICA_REGION_DEFAULT,
    }


@router.post("/check-bucket-name", summary="Check or create S3 bucket")
async def check_bucket_name(
    request: BYOCCheckBucketRequest,
    user: User = Depends(get_current_user),
):
    """Check bucket format; optionally create when name is free (create_if_missing)."""
    check_byoc_eligibility(user.username)
    fmt = validate_bucket_name_format(request.bucket_name)
    if fmt:
        return {"bucket_name": request.bucket_name, "status": "invalid", "message": fmt}

    region = request.region or "ap-south-1"
    access_key_id, secret_access_key, session_token = _resolve_aws_session_creds(
        user.username,
        request.connection_method,
        region,
        request.access_key_id,
        request.secret_access_key,
        request.role_arn,
    )
    if request.session_token:
        session_token = request.session_token

    status = check_bucket_access(
        access_key_id,
        secret_access_key,
        request.bucket_name,
        region,
        session_token,
    )

    if status == "available" and request.create_if_missing:
        ok, create_message = create_s3_bucket(
            access_key_id,
            secret_access_key,
            request.bucket_name,
            region,
            session_token,
        )
        if not ok:
            return {
                "bucket_name": request.bucket_name,
                "status": "forbidden",
                "message": create_message,
            }
        return {
            "bucket_name": request.bucket_name,
            "status": "accessible",
            "message": create_message,
            "created": True,
        }

    messages = {
        "available": "Name is available — Zenith will create this bucket when you connect.",
        "accessible": "Bucket exists and your credentials can access it.",
        "forbidden": "Bucket unavailable or access denied (name may be taken globally).",
        "invalid": "Invalid bucket name format.",
    }
    return {
        "bucket_name": request.bucket_name,
        "status": status,
        "message": messages.get(status, ""),
        "created": False,
    }


@router.get("/policy-templates", summary="Get IAM Policy Templates")
async def get_policy_templates(user: User = Depends(get_current_user)):
    """Get IAM policy templates with user-specific external ID."""
    check_byoc_eligibility(user.username)
    
    ext_id = get_or_create_external_id(user.username)
    
    # Deep copy and inject user-specific values
    import copy, json
    templates = copy.deepcopy(IAM_POLICY_TEMPLATES)
    
    # Inject external ID into AWS IAM Role trust policy
    aws_role = templates["AWS"]["iam_role"]
    trust_json = json.dumps(aws_role["trust_policy"])
    trust_json = trust_json.replace("EXTERNAL_ID_PLACEHOLDER", ext_id)
    aws_role["trust_policy"] = json.loads(trust_json)
    
    # Inject into setup steps
    aws_role["setup_steps"] = [
        step.replace("{account_id}", ZENITH_AWS_ACCOUNT_ID).replace("{external_id}", ext_id)
        for step in aws_role["setup_steps"]
    ]
    aws_role["external_id"] = ext_id
    aws_role["zenith_account_id"] = ZENITH_AWS_ACCOUNT_ID
    
    return templates


@router.post("/connect", summary="Connect BYOC Cloud Account")
async def connect_cloud(request: BYOCConnectRequest, user: User = Depends(get_current_user)):
    """Connect a user's own cloud account. Tests before saving."""
    check_byoc_eligibility(user.username)
    
    csp = request.csp.upper()
    if csp not in ("AWS", "GCP", "AZURE"):
        raise HTTPException(status_code=400, detail="Invalid CSP. Must be AWS, GCP, or Azure.")
    
    test_result = None
    credentials_to_encrypt = {}
    bucket_or_container = ""
    
    if csp == "AWS":
        primary_region = request.primary_region or request.region or "ap-south-1"
        replica_region = request.replica_region or REPLICA_REGION_DEFAULT
        storage_bucket = _resolve_aws_storage_bucket(request)
        secure_bucket = (request.secure_bucket_name or storage_bucket).strip()
        replica_bucket = (request.replica_bucket_name or "").strip()

        if not storage_bucket or not secure_bucket:
            raise HTTPException(
                status_code=400,
                detail="storage_bucket_name and secure_bucket_name are required.",
            )
        if request.secure_dual_write and not replica_bucket:
            raise HTTPException(
                status_code=400,
                detail="replica_bucket_name is required when secure replication is enabled.",
            )

        for name, label in [
            (storage_bucket, "Storage bucket"),
            (secure_bucket, "Secure bucket"),
            (replica_bucket, "Replica bucket") if replica_bucket else (None, None),
        ]:
            if not name:
                continue
            fmt_err = validate_bucket_name_format(name)
            if fmt_err:
                raise HTTPException(status_code=400, detail=f"{label}: {fmt_err}")

        session_token = None
        access_key_id = request.access_key_id
        secret_access_key = request.secret_access_key

        if request.connection_method == "iam_role":
            if not request.role_arn:
                raise HTTPException(status_code=400, detail="IAM Role method requires role_arn.")
            ext_id = get_or_create_external_id(user.username)
            credentials_to_encrypt = {
                "role_arn": request.role_arn,
                "external_id": ext_id,
                "region": primary_region,
            }
        else:
            credentials_to_encrypt = {
                "access_key_id": request.access_key_id,
                "secret_access_key": request.secret_access_key,
                "region": primary_region,
            }

        access_key_id, secret_access_key, session_token = _resolve_aws_session_creds(
            user.username,
            request.connection_method,
            primary_region,
            request.access_key_id,
            request.secret_access_key,
            request.role_arn,
        )

        buckets_to_test = [
            (storage_bucket, primary_region),
            (secure_bucket, primary_region),
        ]
        if request.secure_dual_write and replica_bucket:
            buckets_to_test.append((replica_bucket, replica_region))

        ok, bucket_message = ensure_aws_buckets_exist(
            access_key_id,
            secret_access_key,
            buckets_to_test,
            session_token,
        )
        if not ok:
            raise HTTPException(status_code=400, detail=bucket_message)

        _save_aws_byoc_record(
            user,
            request,
            credentials_to_encrypt,
            storage_bucket,
            secure_bucket,
            replica_bucket if request.secure_dual_write else "",
            primary_region,
            replica_region,
        )
        logger.info(
            "BYOC: %s connected AWS (storage=%s secure=%s replica=%s)",
            user.username,
            storage_bucket,
            secure_bucket,
            replica_bucket,
        )
        connect_message = "AWS account connected. Storage and Security will use your buckets."
        if bucket_message and "Created" in bucket_message:
            connect_message = f"{connect_message} {bucket_message}"

        return {
            "success": True,
            "message": connect_message,
            "csp": "AWS",
            "connection_method": request.connection_method,
            "storage_bucket_name": storage_bucket,
            "secure_bucket_name": secure_bucket,
            "replica_bucket_name": replica_bucket if request.secure_dual_write else None,
            "primary_region": primary_region,
            "replica_region": replica_region,
            "secure_dual_write": request.secure_dual_write,
            "bucket_name": storage_bucket,
        }
    
    elif csp == "GCP":
        if not request.service_account_json or not request.gcp_bucket_name:
            raise HTTPException(status_code=400, detail="GCP requires service_account_json and gcp_bucket_name.")
        
        test_result = test_gcp_credentials(request.service_account_json, request.gcp_bucket_name)
        credentials_to_encrypt = {"service_account_json": request.service_account_json}
        bucket_or_container = request.gcp_bucket_name
    
    elif csp == "AZURE":
        if not request.account_name or not request.account_key or not request.container_name:
            raise HTTPException(status_code=400, detail="Azure requires account_name, account_key, and container_name.")
        
        test_result = test_azure_credentials(request.account_name, request.account_key, request.container_name)
        credentials_to_encrypt = {"account_name": request.account_name, "account_key": request.account_key}
        bucket_or_container = request.container_name
    
    if not test_result.success:
        raise HTTPException(status_code=400, detail={"message": test_result.message, "csp": csp, "success": False})

    encrypted_creds = encrypt_credentials_dict(credentials_to_encrypt)

    byoc_collection.update_one(
        {"username": user.username, "csp": csp},
        {"$set": {
            "username": user.username,
            "csp": csp,
            "connection_method": request.connection_method,
            "credentials": encrypted_creds,
            "bucket_name": bucket_or_container if csp != "AZURE" else "",
            "container_name": bucket_or_container if csp == "AZURE" else "",
            "is_active": True,
            "updated_at": datetime.utcnow(),
        },
        "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )

    logger.info(f"BYOC: {user.username} connected {csp} account (method: {request.connection_method})")

    return {
        "success": True,
        "message": test_result.message,
        "csp": csp,
        "bucket_name": bucket_or_container,
        "connection_method": request.connection_method,
    }


@router.post("/test", summary="Test BYOC Credentials")
async def test_credentials(request: BYOCConnectRequest, user: User = Depends(get_current_user)):
    """Test credentials without saving them."""
    check_byoc_eligibility(user.username)
    
    csp = request.csp.upper()
    
    if csp == "AWS":
        if request.connection_method == "iam_role":
            ext_id = get_or_create_external_id(user.username)
            result = test_aws_iam_role(request.role_arn, ext_id, request.bucket_name, request.region or "ap-south-1")
        else:
            result = test_aws_access_keys(request.access_key_id, request.secret_access_key, request.bucket_name, request.region or "ap-south-1")
    elif csp == "GCP":
        result = test_gcp_credentials(request.service_account_json, request.gcp_bucket_name)
    elif csp == "AZURE":
        result = test_azure_credentials(request.account_name, request.account_key, request.container_name)
    else:
        raise HTTPException(status_code=400, detail="Invalid CSP.")
    
    return result


@router.delete("/disconnect/{csp}", summary="Disconnect BYOC Cloud Account")
async def disconnect_cloud(csp: str, user: User = Depends(get_current_user)):
    """Disconnect a BYOC cloud account."""
    csp = csp.upper()
    if csp not in ("AWS", "GCP", "AZURE"):
        raise HTTPException(status_code=400, detail="Invalid CSP.")
    
    result = byoc_collection.update_one(
        {"username": user.username, "csp": csp},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"No BYOC connection found for {csp}.")
    
    logger.info(f"BYOC: {user.username} disconnected {csp} account")
    
    return {
        "success": True,
        "message": f"{csp} account disconnected. Operations will use Zenith's managed infrastructure.",
        "csp": csp
    }
