# Secure Cloud Integration Guide

## Overview
This document explains how to implement secure cloud credential management for your SaaS platform, where users connect their own cloud accounts without sharing full credentials.

## Current Architecture (Insecure - DO NOT USE IN PRODUCTION)

```
❌ User provides full AWS/GCP/Azure credentials to you
❌ You store credentials in your database
❌ You use their credentials to manage resources
❌ Security risk: Full account access, credential leaks
```

## Recommended Architecture (Secure - Production Ready)

### **Option 1: OAuth 2.0 / OpenID Connect (Best for SaaS)**

Users authorize your app to access specific resources without sharing credentials.

#### **AWS: IAM Roles with External ID**

```python
# backend/app/cloud/aws_integration.py

import boto3
from app.database.mongo_client import get_database

def connect_user_aws_account(user_id: str, role_arn: str, external_id: str):
    """
    User creates an IAM role in their AWS account with specific permissions.
    Your app assumes that role with an external ID for security.
    """
    
    # Store role ARN and external ID (NOT credentials)
    db = get_database()
    db["cloud_connections"].update_one(
        {"user_id": user_id, "provider": "aws"},
        {
            "$set": {
                "role_arn": role_arn,
                "external_id": external_id,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

def get_user_aws_session(user_id: str):
    """
    Assume the user's IAM role to get temporary credentials.
    """
    db = get_database()
    connection = db["cloud_connections"].find_one({
        "user_id": user_id,
        "provider": "aws"
    })
    
    if not connection:
        raise Exception("AWS account not connected")
    
    # Use STS to assume role with external ID
    sts_client = boto3.client('sts')
    assumed_role = sts_client.assume_role(
        RoleArn=connection["role_arn"],
        RoleSessionName=f"zenith-session-{user_id}",
        ExternalId=connection["external_id"],
        DurationSeconds=3600  # 1 hour
    )
    
    # Return temporary credentials (auto-expire)
    return boto3.Session(
        aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
        aws_session_token=assumed_role['Credentials']['SessionToken']
    )
```

**User Setup Steps:**
1. User creates IAM role in their AWS account
2. Adds your app's AWS account as trusted entity
3. Sets specific permissions (read S3, manage EC2, etc.)
4. Provides role ARN to your app
5. You use STS AssumeRole with external ID

**Benefits:**
- ✅ No credential storage
- ✅ Limited permissions (user controls)
- ✅ Temporary credentials (auto-expire)
- ✅ External ID prevents confused deputy attacks

---

#### **GCP: Service Account Impersonation**

```python
# backend/app/cloud/gcp_integration.py

from google.auth import impersonated_credentials
from google.cloud import compute_v1
from app.database.mongo_client import get_database

def connect_user_gcp_account(user_id: str, service_account_email: str):
    """
    User creates a service account in their GCP project.
    Grants your service account permission to impersonate theirs.
    """
    
    db = get_database()
    db["cloud_connections"].update_one(
        {"user_id": user_id, "provider": "gcp"},
        {
            "$set": {
                "service_account_email": service_account_email,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

def get_user_gcp_credentials(user_id: str):
    """
    Impersonate user's service account to get temporary credentials.
    """
    db = get_database()
    connection = db["cloud_connections"].find_one({
        "user_id": user_id,
        "provider": "gcp"
    })
    
    if not connection:
        raise Exception("GCP account not connected")
    
    # Your app's credentials
    source_credentials, project_id = google.auth.default()
    
    # Impersonate user's service account
    target_scopes = [
        'https://www.googleapis.com/auth/compute',
        'https://www.googleapis.com/auth/cloud-platform'
    ]
    
    credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=connection["service_account_email"],
        target_scopes=target_scopes,
        lifetime=3600  # 1 hour
    )
    
    return credentials
```

**User Setup Steps:**
1. User creates service account in their GCP project
2. Grants your service account `roles/iam.serviceAccountTokenCreator` on theirs
3. Provides service account email to your app
4. You impersonate their account with limited permissions

---

#### **Azure: Managed Identity + RBAC**

```python
# backend/app/cloud/azure_integration.py

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from app.database.mongo_client import get_database

def connect_user_azure_account(user_id: str, tenant_id: str, subscription_id: str):
    """
    User creates an App Registration in Azure AD.
    Grants your app specific RBAC roles in their subscription.
    """
    
    db = get_database()
    db["cloud_connections"].update_one(
        {"user_id": user_id, "provider": "azure"},
        {
            "$set": {
                "tenant_id": tenant_id,
                "subscription_id": subscription_id,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

def get_user_azure_client(user_id: str):
    """
    Use Azure RBAC to access user's resources with limited permissions.
    """
    db = get_database()
    connection = db["cloud_connections"].find_one({
        "user_id": user_id,
        "provider": "azure"
    })
    
    if not connection:
        raise Exception("Azure account not connected")
    
    # Use your app's managed identity
    credential = DefaultAzureCredential()
    
    compute_client = ComputeManagementClient(
        credential=credential,
        subscription_id=connection["subscription_id"]
    )
    
    return compute_client
```

---

### **Option 2: API Keys with Limited Scopes (Simpler but Less Secure)**

If OAuth is too complex, use API keys with limited permissions:

```python
# backend/app/cloud/api_key_integration.py

from cryptography.fernet import Fernet
import os

# Encryption key (store in environment variable)
ENCRYPTION_KEY = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY.encode())

def store_encrypted_credentials(user_id: str, provider: str, access_key: str, secret_key: str):
    """
    Encrypt and store user's API keys.
    ONLY if they create limited-scope keys.
    """
    
    # Encrypt credentials
    encrypted_access = cipher.encrypt(access_key.encode()).decode()
    encrypted_secret = cipher.encrypt(secret_key.encode()).decode()
    
    db = get_database()
    db["cloud_connections"].update_one(
        {"user_id": user_id, "provider": provider},
        {
            "$set": {
                "encrypted_access_key": encrypted_access,
                "encrypted_secret_key": encrypted_secret,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

def get_decrypted_credentials(user_id: str, provider: str):
    """
    Decrypt and return temporary credentials.
    """
    db = get_database()
    connection = db["cloud_connections"].find_one({
        "user_id": user_id,
        "provider": provider
    })
    
    if not connection:
        raise Exception(f"{provider} account not connected")
    
    access_key = cipher.decrypt(connection["encrypted_access_key"].encode()).decode()
    secret_key = cipher.decrypt(connection["encrypted_secret_key"].encode()).decode()
    
    return access_key, secret_key
```

**Important:**
- ✅ Encrypt credentials at rest
- ✅ Require users to create limited-scope keys
- ✅ Never log credentials
- ✅ Rotate encryption keys regularly

---

## Implementation Roadmap

### **Phase 1: Short-term (Current Sprint)**
1. Add encryption for existing credentials
2. Update docs to require limited IAM permissions
3. Add credential validation endpoints

### **Phase 2: Medium-term (Next 2 sprints)**
1. Implement AWS IAM Role assumption
2. Add GCP service account impersonation
3. Create user onboarding flow for cloud connection

### **Phase 3: Long-term (Production)**
1. Full OAuth 2.0 integration
2. Azure RBAC implementation
3. Audit logging for all cloud operations
4. Credential expiration and rotation

---

## User-Facing Documentation

### **How to Connect Your AWS Account Securely**

**Step 1: Create IAM Role**
```bash
# In AWS Console:
1. Go to IAM → Roles → Create Role
2. Select "Another AWS account"
3. Enter Zenith's AWS Account ID: 123456789012
4. Require External ID: <copy from Zenith dashboard>
5. Attach policy: ZenithLimitedAccessPolicy
```

**Step 2: Set Permissions**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "*"
    }
  ]
}
```

**Step 3: Connect to Zenith**
1. Copy Role ARN
2. Paste in Zenith Dashboard → Cloud Connections
3. Click "Connect AWS Account"
4. ✅ Done! No credentials shared.

---

## Security Best Practices

1. **Never Store Plain-text Credentials**
   - Use encryption at rest
   - Use environment variables for keys
   - Rotate encryption keys quarterly

2. **Principle of Least Privilege**
   - Request minimum permissions needed
   - Document required IAM policies
   - Allow users to customize permissions

3. **Audit Logging**
   - Log all credential access
   - Log all cloud API calls
   - Monitor for suspicious activity

4. **Compliance**
   - SOC 2 Type II certification
   - GDPR compliance for EU users
   - Regular security audits

---

## Example: Updated VM Manager with IAM Roles

```python
# backend/app/vm/manager.py

from app.cloud.aws_integration import get_user_aws_session
from app.cloud.gcp_integration import get_user_gcp_credentials

async def create_vm_for_user(user_id: str, vm_config: dict):
    """
    Create VM using user's own cloud credentials (securely).
    """
    
    if vm_config["provider"] == "aws":
        # Get temporary credentials via IAM role assumption
        session = get_user_aws_session(user_id)
        ec2 = session.client('ec2')
        
        response = ec2.run_instances(
            ImageId=vm_config["image_id"],
            InstanceType=vm_config["instance_type"],
            MinCount=1,
            MaxCount=1
        )
        
        return response['Instances'][0]['InstanceId']
    
    elif vm_config["provider"] == "gcp":
        # Get credentials via service account impersonation
        credentials = get_user_gcp_credentials(user_id)
        instance_client = compute_v1.InstancesClient(credentials=credentials)
        
        # Create VM with user's credentials
        # ... (existing GCP code)
```

---

## Conclusion

**Recommended Approach:**
- ✅ AWS: IAM Roles with External ID
- ✅ GCP: Service Account Impersonation
- ✅ Azure: Managed Identity + RBAC
- ✅ Encrypt any stored keys
- ✅ Document security clearly for users

This approach:
- Builds trust with users
- Reduces your liability
- Follows industry best practices
- Makes your SaaS enterprise-ready

**Next Steps:**
1. Implement AWS IAM role integration first (most common)
2. Create user onboarding flow with clear instructions
3. Add security badges to your landing page
4. Get SOC 2 audit when you have customers

---

**Author:** GitHub Copilot  
**Date:** November 30, 2025  
**Version:** 1.0
