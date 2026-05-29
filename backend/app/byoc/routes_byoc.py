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
from app.byoc.credential_resolver import get_byoc_status
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
                        "Sid": "ZenithStorageAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:PutObject",
                            "s3:GetObject",
                            "s3:DeleteObject",
                            "s3:ListBucket",
                            "s3:GetBucketLocation"
                        ],
                        "Resource": [
                            "arn:aws:s3:::YOUR_BUCKET_NAME",
                            "arn:aws:s3:::YOUR_BUCKET_NAME/*"
                        ]
                    }
                ]
            },
            "setup_steps": [
                "Go to AWS Console → IAM → Roles → Create Role",
                "Select 'Another AWS account' as trusted entity",
                "Enter Zenith's Account ID: {account_id}",
                "Check 'Require external ID' and enter: {external_id}",
                "Click Next → Create a policy with the permissions JSON below (replace YOUR_BUCKET_NAME)",
                "Attach the policy → Name the role 'ZenithBYOC' → Create",
                "Copy the Role ARN (e.g., arn:aws:iam::123456789012:role/ZenithBYOC)",
                "Paste the Role ARN below"
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
    bucket_name: Optional[str] = Field(None, description="S3 bucket name")
    region: Optional[str] = Field("ap-south-1", description="AWS region")
    
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
        if request.connection_method == "iam_role":
            # IAM Role method — use Role ARN
            if not request.role_arn or not request.bucket_name:
                raise HTTPException(status_code=400, detail="IAM Role method requires role_arn and bucket_name.")
            
            ext_id = get_or_create_external_id(user.username)
            test_result = test_aws_iam_role(request.role_arn, ext_id, request.bucket_name, request.region or "ap-south-1")
            credentials_to_encrypt = {
                "role_arn": request.role_arn,
                "external_id": ext_id,
                "region": request.region or "ap-south-1",
            }
        else:
            # Access Keys method
            if not request.access_key_id or not request.secret_access_key or not request.bucket_name:
                raise HTTPException(status_code=400, detail="Access Keys method requires access_key_id, secret_access_key, and bucket_name.")
            
            test_result = test_aws_access_keys(request.access_key_id, request.secret_access_key, request.bucket_name, request.region or "ap-south-1")
            credentials_to_encrypt = {
                "access_key_id": request.access_key_id,
                "secret_access_key": request.secret_access_key,
                "region": request.region or "ap-south-1",
            }
        bucket_or_container = request.bucket_name
    
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
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }},
        upsert=True
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
