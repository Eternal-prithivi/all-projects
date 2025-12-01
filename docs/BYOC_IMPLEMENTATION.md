# BYOC (Bring Your Own Cloud) Implementation Guide

## Overview

Zenith offers two deployment modes:
1. **Managed Cloud** (Default) - Use our infrastructure
2. **BYOC** (Enterprise) - Connect your cloud account

## Architecture

### Default Mode: Zenith-Managed Cloud

```
User → Zenith Platform → Our AWS/GCP Account → User's Resources
```

**Pricing:**
- Free: 1 VM, 5GB storage
- Basic ($20/mo): 3 VMs, 50GB storage  
- Pro ($50/mo): 10 VMs, 200GB storage

**Benefits:**
- ✅ Instant setup
- ✅ No cloud expertise needed
- ✅ We handle security, backups, monitoring
- ✅ One bill (no AWS/GCP invoice)

### BYOC Mode: User's Cloud Account

```
User → Zenith Platform → User's AWS/GCP Account → User's Resources
```

**Pricing:**
- Enterprise ($99/mo): Unlimited resources + service fee
- User pays cloud provider directly

**Benefits:**
- ✅ Full control over resources
- ✅ Lower cost at scale (no markup)
- ✅ Compliance requirements met
- ✅ Data stays in your account

---

## Database Schema

```python
# MongoDB: users collection
{
  "username": "john_doe",
  "email": "john@company.com",
  "subscription_plan": "pro",  # or "enterprise-byoc"
  "cloud_mode": "managed",     # or "byoc"
  "cloud_connection": {
    "provider": "aws",         # null if managed mode
    "method": "iam_role",      # or "api_keys"
    "role_arn": "arn:aws:...", # only for BYOC
    "external_id": "zenith-abc123"
  }
}
```

---

## Backend Implementation

### 1. Cloud Manager Factory Pattern

```python
# backend/app/cloud/manager_factory.py

from app.database.mongo_client import get_database
from .managed_cloud import ManagedCloudManager
from .byoc_cloud import BYOCCloudManager

def get_cloud_manager(user_id: str):
    """
    Return appropriate cloud manager based on user's mode.
    """
    db = get_database()
    user = db["users"].find_one({"_id": user_id})
    
    if user.get("cloud_mode") == "byoc":
        # Use their cloud account
        return BYOCCloudManager(user)
    else:
        # Use our cloud account (default)
        return ManagedCloudManager(user)
```

### 2. Managed Cloud Manager

```python
# backend/app/cloud/managed_cloud.py

import boto3
from app.config import settings

class ManagedCloudManager:
    """
    Manages resources using Zenith's cloud accounts.
    """
    
    def __init__(self, user):
        self.user = user
        # Use OUR credentials
        self.aws_session = boto3.Session(
            aws_access_key_id=settings.ZENITH_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.ZENITH_AWS_SECRET_KEY,
            region_name=settings.AWS_REGION
        )
    
    def create_vm(self, config):
        """
        Create VM in our AWS account, tag with user ID.
        """
        ec2 = self.aws_session.client('ec2')
        
        response = ec2.run_instances(
            ImageId=config["image_id"],
            InstanceType=config["instance_type"],
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'ZenithUser', 'Value': self.user["_id"]},
                    {'Key': 'Plan', 'Value': self.user["subscription_plan"]},
                    {'Key': 'ManagedBy', 'Value': 'Zenith'}
                ]
            }]
        )
        
        return response['Instances'][0]['InstanceId']
    
    def check_quota(self, resource_type):
        """
        Check if user is within plan limits.
        """
        plan_limits = {
            "free": {"vms": 1, "storage_gb": 5},
            "basic": {"vms": 3, "storage_gb": 50},
            "pro": {"vms": 10, "storage_gb": 200}
        }
        
        current_usage = self._get_user_usage()
        plan = self.user.get("subscription_plan", "free")
        limit = plan_limits[plan][resource_type]
        
        if current_usage[resource_type] >= limit:
            raise Exception(f"Plan limit reached. Upgrade to get more {resource_type}.")
        
        return True
```

### 3. BYOC Cloud Manager

```python
# backend/app/cloud/byoc_cloud.py

import boto3
from .aws_integration import get_user_aws_session

class BYOCCloudManager:
    """
    Manages resources using user's cloud account.
    """
    
    def __init__(self, user):
        self.user = user
        # Use THEIR credentials via IAM role
        self.aws_session = get_user_aws_session(user["_id"])
    
    def create_vm(self, config):
        """
        Create VM in user's AWS account.
        """
        ec2 = self.aws_session.client('ec2')
        
        response = ec2.run_instances(
            ImageId=config["image_id"],
            InstanceType=config["instance_type"],
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'ManagedBy', 'Value': 'Zenith'},
                    {'Key': 'ZenithUser', 'Value': self.user["username"]}
                ]
            }]
        )
        
        return response['Instances'][0]['InstanceId']
    
    def check_quota(self, resource_type):
        """
        No quota limits - user pays for their own resources.
        """
        return True
```

### 4. Update VM Routes

```python
# backend/app/vm/routes_vm.py

from app.cloud.manager_factory import get_cloud_manager

@router.post("/request")
async def request_vm(
    config: VMConfig,
    current_user: dict = Depends(get_current_user)
):
    """
    Request VM - works for both managed and BYOC modes.
    """
    
    # Get appropriate cloud manager
    cloud_manager = get_cloud_manager(current_user["_id"])
    
    # Check quota (managed) or skip (BYOC)
    cloud_manager.check_quota("vms")
    
    # Create VM in appropriate cloud account
    vm_id = cloud_manager.create_vm(config.dict())
    
    return {"vm_id": vm_id, "mode": current_user.get("cloud_mode", "managed")}
```

---

## Frontend Implementation

### 1. Settings Page - Cloud Connection

```jsx
// frontend/src/pages/CloudConnectionPage.jsx

import React, { useState } from 'react';
import { apiClient } from '../api';

function CloudConnectionPage() {
  const [cloudMode, setCloudMode] = useState('managed'); // or 'byoc'
  
  return (
    <div className="cloud-connection-page">
      <h1>Cloud Account Settings</h1>
      
      <div className="cloud-mode-selector">
        <div className={`mode-card ${cloudMode === 'managed' ? 'active' : ''}`}>
          <h3>🚀 Zenith-Managed Cloud (Default)</h3>
          <p>We handle everything - just focus on your work</p>
          <ul>
            <li>✅ Instant setup</li>
            <li>✅ No cloud expertise needed</li>
            <li>✅ Predictable pricing</li>
            <li>✅ Full support</li>
          </ul>
          <button onClick={() => setCloudMode('managed')}>
            Use Zenith Cloud
          </button>
        </div>
        
        <div className={`mode-card ${cloudMode === 'byoc' ? 'active' : ''}`}>
          <h3>🔐 Bring Your Own Cloud (Enterprise)</h3>
          <p>Connect your AWS/GCP/Azure account</p>
          <ul>
            <li>✅ Full control</li>
            <li>✅ Lower cost at scale</li>
            <li>✅ Compliance ready</li>
            <li>✅ Data in your account</li>
          </ul>
          <button onClick={() => setCloudMode('byoc')}>
            Connect My Cloud
          </button>
        </div>
      </div>
      
      {cloudMode === 'byoc' && (
        <div className="byoc-setup">
          <h3>Connect Your AWS Account</h3>
          
          <div className="setup-steps">
            <h4>Step 1: Create IAM Role</h4>
            <code>
              1. Go to AWS Console → IAM → Roles<br/>
              2. Create role for "Another AWS account"<br/>
              3. Account ID: 123456789012 (Zenith's)<br/>
              4. External ID: {user.external_id}
            </code>
            
            <h4>Step 2: Enter Role ARN</h4>
            <input 
              type="text" 
              placeholder="arn:aws:iam::123456789:role/ZenithAccess"
              onChange={(e) => setRoleArn(e.target.value)}
            />
            
            <button onClick={connectAWS}>Connect AWS Account</button>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 2. Pricing Page Update

```jsx
// frontend/src/pages/PricingPage.jsx - Add Enterprise Plan

const plans = [
  {
    name: "Free",
    price: 0,
    features: [
      "1 VM (Zenith-managed)",
      "5GB Storage",
      "Community support"
    ]
  },
  {
    name: "Pro",
    price: 50,
    features: [
      "10 VMs (Zenith-managed)",
      "200GB Storage",
      "Priority support"
    ]
  },
  {
    name: "Enterprise (BYOC)",
    price: 99,
    badge: "Popular",
    features: [
      "Unlimited resources",
      "Use YOUR cloud account",
      "Pay cloud costs directly",
      "Lower total cost at scale",
      "IAM role security",
      "Dedicated support"
    ]
  }
];
```

---

## Pricing Strategy

### Managed Cloud (Your Revenue)

```
VM Cost Breakdown:
- AWS t3.medium: $30/mo
- Your price: $50/mo
- Your profit: $20/mo (40% margin)

Storage Cost:
- S3 50GB: $1.15/mo
- Your price: $5/mo
- Your profit: $3.85/mo (77% margin)
```

### BYOC (Service Fee)

```
Enterprise Plan: $99/mo flat fee
- User runs 100 VMs: $3,000/mo → AWS (they pay)
- Your fee: $99/mo
- Their savings: ~$400/mo vs managed

Profit per user:
- Managed (10 VMs): $200/mo profit
- BYOC (100 VMs): $99/mo profit (but easier to manage!)
```

---

## Migration Path

### Phase 1 (Current - MVP)
- ✅ Everyone uses managed cloud
- ✅ Simple pricing
- ✅ Fast onboarding

### Phase 2 (Growth - 100+ users)
- Add BYOC option
- Enterprise plan pricing
- IAM role documentation

### Phase 3 (Scale - 1000+ users)
- Hybrid billing
- Cost optimization dashboard
- White-label option

---

## User Journey

### Small Team (Managed)
```
Day 1: Sign up → Get 1 free VM → Works instantly
Day 30: Upgrade to Pro ($50/mo) → Get 10 VMs
Day 180: Happy with service, stay on Pro
```

### Enterprise (BYOC)
```
Day 1: Sign up → See BYOC option
Day 2: Contact sales → Get guidance
Day 7: Set up IAM role → Connect AWS
Day 30: Pay $99/mo + their AWS bill
Day 180: Run 500 VMs → Save $5,000/mo vs managed
```

---

## Security & Compliance

### Managed Mode
- ✅ We handle SOC 2
- ✅ We manage encryption
- ✅ We do backups
- ✅ Simpler for users

### BYOC Mode
- ✅ User's compliance (their account)
- ✅ IAM roles (no credentials stored)
- ✅ Audit trail in their CloudTrail
- ✅ Enterprise-ready

---

## Competitive Advantage

**This is exactly what successful SaaS companies do:**

- **Heroku**: Managed dynos OR connect AWS
- **Vercel**: Vercel cloud OR enterprise BYOC
- **Databricks**: Managed cluster OR customer cloud
- **Snowflake**: Snowflake account OR BYOC data

**You're following the industry standard!** ✅

---

## Next Steps

1. **Keep current managed cloud** - it works!
2. **Add "Enterprise (BYOC)" plan** to pricing page (grayed out)
3. **Add "Coming Soon" badge** - builds interest
4. **Implement BYOC** when first enterprise customer asks
5. **Charge $99/mo service fee** - profitable!

---

**This is the PERFECT business model for cloud SaaS!** 🎉
