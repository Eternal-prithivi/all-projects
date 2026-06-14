# BYOC (Bring Your Own Cloud) Implementation Guide

> **Trust & encryption (user-facing):** [security/TRUST_AND_ENCRYPTION.md](./security/TRUST_AND_ENCRYPTION.md)  
> **Credential encryption (technical):** [security/BYOC_CREDENTIAL_ENCRYPTION.md](./security/BYOC_CREDENTIAL_ENCRYPTION.md)  
> **Tri-cloud parity:** [cloud/MULTI_CLOUD_PARITY_MATRIX.md](./cloud/MULTI_CLOUD_PARITY_MATRIX.md)

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

## Backend Implementation (as built)

Zenith does **not** use a `manager_factory.py` / `BYOCCloudManager` class hierarchy. Routing is implemented with:

| Layer | Module | Role |
|-------|--------|------|
| Credential store | `backend/app/byoc/routes_byoc.py` | Connect / disconnect / encrypt BYOC records |
| Resolver | `backend/app/byoc/credential_resolver.py` | `resolve_*_credentials(username)` — BYOC first, else platform `.env` |
| Feature gates | `backend/app/byoc/capabilities.py` | Per-CSP feature readiness (storage, vm, provision, cost) |
| Availability | `backend/app/cloud/availability.py` | Hybrid union of BYOC + platform per feature |
| VM runtime | `aws_runtime.py`, `gcp_runtime.py`, `azure_runtime.py` | Per-request `contextvars` bind username → resolver |
| VM dispatch | `backend/app/vm/vm_provider.py` | Routes create/start/stop/list to `aws_manager` / `manager` (GCP) / `azure_manager` |
| Provision | `backend/app/provision/byoc_credentials.py` | Terraform/Boto3/SDK env from resolver |

### VM request flow (implemented)

```python
# backend/app/vm/routes_vm.py (simplified)

@router.post("/request")
async def request_vm_assignment(request, current_user):
    provider = normalize_provider(request.csp or "GCP")
    assert_byoc_feature_ready(current_user.username, provider, CloudFeature.VM)
    assert_provider_available(current_user.username, provider, CloudFeature.VM)
    with vm_runtime_context(current_user.username, provider, region_slug):
        vm_name, vm_ip, ... = assign_vm_to_user(..., csp=provider)
```

Inside `vm_runtime_context`, AWS/GCP/Azure managers call cloud APIs with **the user's BYOC credentials** when that CSP is connected.

### Per-CSP BYOC requirements for VMs

| CSP | Minimum BYOC for VM | Notes |
|-----|---------------------|-------|
| **AWS** | Access keys or IAM role (storage connect) | EC2 uses same resolved creds; IAM role assume still needs platform STS keys |
| **GCP** | Service account JSON (storage connect) | Compute zone derived from `gcp_primary_location` on the BYOC record; optional `gcp_compute_zone` |
| **Azure** | Storage account **plus** service principal (4 fields) | Storage keys alone cannot create VMs — Azure Compute API requires SP; can be supplied in connect step 3 or `PATCH /byoc/azure/compute` |

### Provision flow (implemented)

`routes_provision.py` calls `resolve_provision_terraform_env(username, csp)` which maps BYOC records to subprocess env vars (AWS keys, `GOOGLE_CREDENTIALS`, Azure ARM vars).

See also: [CREDENTIAL_CONTRACT.md](./cloud/CREDENTIAL_CONTRACT.md), [VM_MULTI_CLOUD_SCOPE.md](./cloud/VM_MULTI_CLOUD_SCOPE.md).

---

## Legacy design note (not implemented)

The sections below describing `ManagedCloudManager` / `BYOCCloudManager` / `get_cloud_manager()` were early design sketches. **Do not implement that factory** — extend the resolver + runtime pattern above instead.

<!--
### 1. Cloud Manager Factory Pattern (REMOVED — see table above)

```python
# NOT IN REPO — illustrative only
```
-->

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
