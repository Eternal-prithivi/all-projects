# Cloud Credential Setup Guide - Restore Project After Credential Expiration

**Purpose:** Step-by-step guide to reconfigure the Cloud Resource Optimization Platform with new cloud provider credentials after account expiration or credential loss.

**Last Updated:** November 19, 2025

---

## 📋 TABLE OF CONTENTS

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [AWS Setup](#aws-setup)
4. [Google Cloud Platform (GCP) Setup](#google-cloud-platform-gcp-setup)
5. [Microsoft Azure Setup](#microsoft-azure-setup)
6. [MongoDB Atlas Setup](#mongodb-atlas-setup)
7. [Twilio SMS Setup (Optional)](#twilio-sms-setup-optional)
8. [Backend Configuration](#backend-configuration)
9. [Testing Credentials](#testing-credentials)
10. [Troubleshooting](#troubleshooting)

---

## OVERVIEW

This guide assumes:
- ✅ All previous cloud accounts have expired or credentials are lost
- ✅ You need to create **new free-tier accounts** for AWS, GCP, and Azure
- ✅ The codebase is intact and only needs credential updates
- ✅ You want minimal cost (free-tier usage only)

**What You'll Need:**
- Valid email addresses (can use the same email for all providers)
- Credit/debit card for verification (won't be charged on free tier)
- 2-3 hours for complete setup

---

## PREREQUISITES

### Required Software (Should Already Be Installed)
- Python 3.9+
- Node.js 16+
- MongoDB Compass (optional, for local testing)

### Files You'll Modify
```
backend/
  .env                           # ← Main credential file
  .env.example                   # Reference for variables
```

### Backup Current Configuration (If Any)
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
cp .env .env.backup.old  # Backup old credentials
```

---

## AWS SETUP

### Step 1: Create AWS Free Tier Account

1. **Go to:** https://aws.amazon.com/free/
2. **Click:** "Create a Free Account"
3. **Provide:**
   - Email address
   - Account name (e.g., "CloudOptimization")
   - Password
4. **Verify email** and complete registration
5. **Add payment method** (for verification - won't be charged on free tier)
6. **Choose:** Basic Support Plan (Free)

**Free Tier Limits (12 months):**
- S3: 5 GB storage, 20,000 GET requests, 2,000 PUT requests/month
- EC2: Not used in this project (we use GCP for VMs)
- Cost Explorer API: 50 free API calls/day

---

### Step 2: Create IAM User with Programmatic Access

**Why:** Root account credentials should never be used in code.

1. **Log in to AWS Console:** https://console.aws.amazon.com/
2. **Navigate to:** IAM (Identity and Access Management)
3. **Click:** "Users" → "Create user"
4. **User name:** `cloud-optimization-app`
5. **Access type:** ☑️ Programmatic access (enables API access)
6. **Click:** "Next: Permissions"

---

### Step 3: Attach Policies to IAM User

**Required Permissions:**

1. **AmazonS3FullAccess**
   - Reason: File upload/download/delete operations
   
2. **CostExplorerReadOnlyAccess**
   - Reason: Fetch cost data for dashboard

**How to Attach:**
- Select "Attach existing policies directly"
- Search and check: `AmazonS3FullAccess`
- Search and check: `CostExplorerReadOnlyAccess`
- Click "Next: Tags" → "Next: Review" → "Create user"

---

### Step 4: Save Access Keys

**IMPORTANT:** Keys are shown only once!

```
Access Key ID: AKIAIOSFODNN7EXAMPLE
Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Save these to a secure location** (password manager recommended).

---

### Step 5: Create S3 Buckets

**You need 3 buckets:**

1. **Regular Storage Bucket** (for general files)
2. **Secure Storage Bucket** (for encrypted files)
3. **Replica Bucket** (for secure file backups)

**Creating Buckets:**

1. **Go to:** S3 Console → https://s3.console.aws.amazon.com/
2. **Click:** "Create bucket"

**Bucket 1: Regular Storage**
- **Name:** `cloud-optimization-storage-{your-unique-id}` (e.g., `cloud-optimization-storage-2025`)
- **Region:** `us-east-1` (or your preferred region)
- **Block Public Access:** ☑️ Keep all checked (private bucket)
- **Versioning:** Disabled (to save costs)
- **Encryption:** Server-side encryption with Amazon S3 managed keys (SSE-S3)
- **Click:** "Create bucket"

**Bucket 2: Secure Storage**
- **Name:** `cloud-optimization-secure-{your-unique-id}`
- **Region:** Same as Bucket 1
- **Settings:** Same as Bucket 1
- **Click:** "Create bucket"

**Bucket 3: Replica Storage**
- **Name:** `cloud-optimization-replica-{your-unique-id}`
- **Region:** **Different region** (e.g., `us-west-2` for disaster recovery)
- **Settings:** Same as above
- **Click:** "Create bucket"

---

### Step 6: Enable Cost Explorer

**Why:** Required for cost tracking features.

1. **Go to:** AWS Billing Console → https://console.aws.amazon.com/billing/
2. **Click:** "Cost Explorer" in left sidebar
3. **Click:** "Enable Cost Explorer"
4. **Wait:** Takes up to 24 hours to populate data

**Note:** Cost Explorer API is free for first 50 calls/day.

---

### Step 7: Note Your AWS Credentials

**Save these values:**
```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET_NAME=cloud-optimization-storage-2025
SECURE_S3_BUCKET_NAME=cloud-optimization-secure-2025
REPLICA_S3_BUCKET_NAME=cloud-optimization-replica-2025
PRIMARY_S3_REGION=us-east-1
REPLICA_S3_REGION=us-west-2
```

---

## GOOGLE CLOUD PLATFORM (GCP) SETUP

### Step 1: Create GCP Free Tier Account

1. **Go to:** https://cloud.google.com/free
2. **Click:** "Get started for free"
3. **Sign in** with Google account (or create new one)
4. **Provide:**
   - Country
   - Business/Personal use
   - Credit/debit card (for $1 verification - refunded)
5. **Accept** terms and complete signup

**Free Tier Benefits:**
- $300 credit for 90 days (for all services)
- Always free products after credit expires:
  - 1 f1-micro VM instance (US regions)
  - 5 GB Cloud Storage
  - 1 GB Cloud Functions invocations

---

### Step 2: Create New Project

1. **Go to:** https://console.cloud.google.com/
2. **Click:** Project dropdown (top left) → "New Project"
3. **Project name:** `cloud-optimization-platform`
4. **Project ID:** Will auto-generate (e.g., `cloud-optimization-platform-123456`)
   - **IMPORTANT:** Save this ID!
5. **Click:** "Create"

---

### Step 3: Enable Required APIs

**Navigate to:** APIs & Services → Library

**Enable these APIs:**

1. **Compute Engine API**
   - Search: "Compute Engine API"
   - Click: "Enable"
   - Reason: VM management

2. **Cloud Storage API**
   - Search: "Cloud Storage API"
   - Click: "Enable"
   - Reason: File storage

3. **Cloud Billing API**
   - Search: "Cloud Billing API"
   - Click: "Enable"
   - Reason: Cost tracking

4. **Cloud Monitoring API**
   - Search: "Cloud Monitoring API"
   - Click: "Enable"
   - Reason: VM metrics

---

### Step 4: Create Service Account

**Why:** Allows backend to authenticate with GCP APIs.

1. **Go to:** IAM & Admin → Service Accounts
2. **Click:** "Create Service Account"
3. **Service account name:** `cloud-optimization-backend`
4. **Service account ID:** Will auto-fill
5. **Click:** "Create and Continue"

**Grant Roles (Step 2):**
- **Compute Admin:** Full control over Compute Engine resources
- **Storage Admin:** Full control over Cloud Storage
- **Billing Account Viewer:** Read billing data

**How to add:**
- Click "Select a role"
- Search and select: "Compute Admin"
- Click "+ Add Another Role"
- Search and select: "Storage Admin"
- Repeat for "Billing Account Viewer"
- Click "Continue" → "Done"

---

### Step 5: Create Service Account Key (JSON)

**CRITICAL:** This JSON file is your authentication credential.

1. **In Service Accounts list**, find `cloud-optimization-backend`
2. **Click:** Three dots (⋮) → "Manage keys"
3. **Click:** "Add Key" → "Create new key"
4. **Key type:** JSON (default)
5. **Click:** "Create"

**Download Location:**
- File downloads as: `cloud-optimization-platform-123456-a1b2c3d4e5f6.json`
- **Move it to:** `/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json`

```bash
# Move the downloaded file
mv ~/Downloads/cloud-optimization-platform-*.json \
   /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json

# Secure permissions
chmod 600 /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json
```

---

### Step 6: Create Cloud Storage Bucket

1. **Go to:** Cloud Storage → Buckets
2. **Click:** "Create bucket"

**Bucket Configuration:**
- **Name:** `cloud-optimization-gcp-storage-{unique-id}` (must be globally unique)
- **Location type:** Region
- **Region:** `us-central1` (free tier eligible)
- **Storage class:** Standard
- **Access control:** Uniform
- **Encryption:** Google-managed key
- **Click:** "Create"

---

### Step 7: Set Up Compute Engine Zone

**Choose a free-tier eligible zone:**
- `us-central1-a` ✅ (recommended)
- `us-east1-b` ✅
- `us-west1-b` ✅

**Why:** Only these zones offer f1-micro (free tier) VMs.

---

### Step 8: Note Your GCP Credentials

**Save these values:**
```
GCP_PROJECT_ID=cloud-optimization-platform-123456
GCP_ZONE=us-central1-a
GCP_SERVICE_ACCOUNT_JSON_PATH=/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json
GCP_BUCKET_NAME=cloud-optimization-gcp-storage-2025
```

---

## MICROSOFT AZURE SETUP

### Step 1: Create Azure Free Account

1. **Go to:** https://azure.microsoft.com/free/
2. **Click:** "Start free"
3. **Sign in** with Microsoft account (or create new)
4. **Provide:**
   - Personal information
   - Phone verification (SMS code)
   - Credit/debit card (for identity verification)
5. **Complete** agreement

**Free Tier Benefits:**
- $200 credit for 30 days
- 12 months of popular services free
- Always free services (including 5 GB Blob Storage)

---

### Step 2: Create Storage Account

1. **Go to:** Azure Portal → https://portal.azure.com/
2. **Click:** "Storage accounts" (search in top bar if needed)
3. **Click:** "+ Create"

**Basics:**
- **Subscription:** Azure subscription 1 (default)
- **Resource group:** Click "Create new" → Name: `cloud-optimization-rg`
- **Storage account name:** `cloudoptstorage2025` (lowercase, no hyphens, 3-24 chars)
- **Region:** (US) East US (or your preferred region)
- **Performance:** Standard
- **Redundancy:** Locally-redundant storage (LRS) - cheapest option

**Advanced:**
- Keep defaults

**Networking:**
- **Public access:** Enable

**Data protection:**
- Keep defaults (disable soft delete to save costs)

**Encryption:**
- Keep defaults

**Click:** "Review + create" → "Create"

---

### Step 3: Create Blob Container

1. **Open your storage account:** `cloudoptstorage2025`
2. **Click:** "Containers" in left sidebar
3. **Click:** "+ Container"
4. **Name:** `files`
5. **Public access level:** Private (no anonymous access)
6. **Click:** "Create"

---

### Step 4: Get Storage Account Keys

1. **In storage account**, click "Access keys" (left sidebar under Security + networking)
2. **Click:** "Show" next to key1

**Save these values:**
```
Storage account name: cloudoptstorage2025
Key 1: (long base64 string - copy entire key)
```

---

### Step 5: Set Up Cost Management

1. **Go to:** Cost Management + Billing
2. **Click:** "Cost analysis"
3. **Note:** Data may take 24 hours to appear

---

### Step 6: Note Your Azure Credentials

**Save these values:**
```
AZURE_STORAGE_ACCOUNT_NAME=cloudoptstorage2025
AZURE_STORAGE_ACCOUNT_KEY=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==
AZURE_CONTAINER_NAME=files
```

---

## MONGODB ATLAS SETUP

### Step 1: Create MongoDB Atlas Account (If Needed)

1. **Go to:** https://www.mongodb.com/cloud/atlas/register
2. **Sign up** with email or Google account
3. **Verify email**

---

### Step 2: Create Free Cluster

1. **Click:** "Build a Database"
2. **Choose:** Shared (Free tier)
3. **Cloud Provider:** AWS (or GCP/Azure - doesn't matter)
4. **Region:** Choose closest to you
5. **Cluster Name:** `CloudOptimization`
6. **Click:** "Create"

**Wait 3-5 minutes** for cluster creation.

---

### Step 3: Create Database User

1. **Security tab** → "Database Access"
2. **Click:** "Add New Database User"
3. **Authentication Method:** Password
4. **Username:** `cloud_admin`
5. **Password:** Generate secure password (save it!)
6. **Database User Privileges:** Read and write to any database
7. **Click:** "Add User"

---

### Step 4: Whitelist Your IP

1. **Security tab** → "Network Access"
2. **Click:** "Add IP Address"
3. **Option 1 (Development):** Click "Allow Access from Anywhere" (0.0.0.0/0)
4. **Option 2 (Production):** Add your specific IP
5. **Click:** "Confirm"

---

### Step 5: Get Connection String

1. **Click:** "Connect" on your cluster
2. **Choose:** "Connect your application"
3. **Driver:** Python, Version: 3.12 or later
4. **Copy connection string:**

```
mongodb+srv://cloud_admin:<password>@cloudoptimization.abc123.mongodb.net/?retryWrites=true&w=majority
```

**Replace `<password>` with actual password!**

---

### Step 6: Note Your MongoDB Credentials

**Save this value:**
```
MONGO_CONNECTION_STRING=mongodb+srv://cloud_admin:YourActualPassword@cloudoptimization.abc123.mongodb.net/?retryWrites=true&w=majority
```

---

## REDIS SETUP (REQUIRED FOR CELERY)

**Required for:** Background task processing (file optimization, budget alerts, storage tiering)

### What is Redis?
Redis is an in-memory data store used as a message broker for Celery. It enables:
- Asynchronous task execution
- Scheduled periodic tasks (budget checks every hour)
- Task queuing and distribution

---

### Step 1: Install Redis Locally (macOS)

**Using Homebrew:**

```bash
# Install Redis
brew install redis

# Start Redis server (runs in background)
brew services start redis

# Verify Redis is running
redis-cli ping
```

**Expected response:** `PONG`

---

### Step 2: Verify Redis Connection

**Test connection:**
```bash
redis-cli
```

**In Redis CLI:**
```
127.0.0.1:6379> SET test "Hello Redis"
OK
127.0.0.1:6379> GET test
"Hello Redis"
127.0.0.1:6379> exit
```

---

### Step 3: Note Your Redis Configuration

**Default settings (local development):**
```
REDIS_URL=redis://localhost:6379/0
```

**Explanation:**
- `redis://` - Protocol
- `localhost` - Host (running on your machine)
- `6379` - Default Redis port
- `/0` - Database number (0-15 available)

---

### Alternative: Redis Cloud (Optional - For Production)

**If you want a cloud-hosted Redis instance:**

1. **Go to:** https://redis.com/try-free/
2. **Sign up** for free account
3. **Create database:**
   - Name: `cloud-optimization-celery`
   - Plan: Free (30 MB)
   - Region: Choose closest to you
4. **Get connection details:**
   - Host: `redis-12345.c123.us-east-1-2.ec2.cloud.redislabs.com`
   - Port: `12345`
   - Password: `your-password-here`

**Connection string for Redis Cloud:**
```
REDIS_URL=redis://:your-password@redis-12345.c123.us-east-1-2.ec2.cloud.redislabs.com:12345/0
```

---

### Step 4: Test Celery with Redis

**Create test file:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
cat > test_celery.py << 'EOF'
from app.celery_worker import celery_app

# Test task
@celery_app.task
def test_task(message):
    return f"Task executed: {message}"

# Send task to queue
result = test_task.delay("Hello from Celery!")
print(f"Task ID: {result.id}")
print(f"Task state: {result.state}")
EOF
```

**Start Celery worker in separate terminal:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
celery -A app.celery_worker worker --loglevel=info
```

**Run test in another terminal:**
```bash
python3 test_celery.py
```

**Expected output:**
```
Task ID: a1b2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p
Task state: PENDING
```

---

## TWILIO SMS SETUP (OPTIONAL)

**Required for:** Budget alert SMS notifications

### Step 1: Create Twilio Account

1. **Go to:** https://www.twilio.com/try-twilio
2. **Sign up** with email
3. **Verify** email and phone number

**Free Trial:**
- $15.50 credit (sends ~500 SMS)
- Can only send to verified phone numbers

---

### Step 2: Get Phone Number

1. **Dashboard:** Click "Get a Twilio phone number"
2. **Click:** "Choose this number"
3. **Save the number:** +1 (XXX) XXX-XXXX

---

### Step 3: Get Account SID and Auth Token

1. **Dashboard:** https://console.twilio.com/
2. **Account Info section** shows:
   - **Account SID:** ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   - **Auth Token:** Click "Show" to reveal

---

### Step 4: Verify Your Phone Number (Free Trial)

1. **Phone Numbers** → "Verified Caller IDs"
2. **Click:** "+ Add a new Caller ID"
3. **Enter your phone number**
4. **Receive verification code** and enter it

---

### Step 5: Note Your Twilio Credentials

**Save these values:**
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

---

## BACKEND CONFIGURATION

### Step 1: Create `.env` File

```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
```

**Create new `.env` file:**
```bash
nano .env
```

---

### Step 2: Copy This Template and Fill In Your Values

```bash
# =============================================================================
# MONGODB CONFIGURATION
# =============================================================================
MONGO_CONNECTION_STRING=mongodb+srv://cloud_admin:YourPassword@cloudoptimization.abc123.mongodb.net/?retryWrites=true&w=majority

# =============================================================================
# JWT AUTHENTICATION
# =============================================================================
SECRET_KEY=your-super-secret-key-change-this-to-random-64-char-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# =============================================================================
# AWS CREDENTIALS
# =============================================================================
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET_NAME=cloud-optimization-storage-2025
SECURE_S3_BUCKET_NAME=cloud-optimization-secure-2025
REPLICA_S3_BUCKET_NAME=cloud-optimization-replica-2025
PRIMARY_S3_REGION=us-east-1
REPLICA_S3_REGION=us-west-2
REGULAR_S3_BUCKET_NAME=cloud-optimization-storage-2025

# =============================================================================
# GOOGLE CLOUD PLATFORM (GCP) CREDENTIALS
# =============================================================================
GCP_PROJECT_ID=cloud-optimization-platform-123456
GCP_ZONE=us-central1-a
GCP_SERVICE_ACCOUNT_JSON_PATH=/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json
GCP_BUCKET_NAME=cloud-optimization-gcp-storage-2025

# VM Cluster Configuration (Optional - can keep defaults)
PERFORMANCE_CLUSTER_MAX_VMS=2
STORAGE_CLUSTER_MAX_VMS=2
PERFORMANCE_VM_MACHINE_TYPE=e2-micro
STORAGE_VM_MACHINE_TYPE=e2-medium
STORAGE_VM_DISK_SIZE_GB=100

# =============================================================================
# MICROSOFT AZURE CREDENTIALS
# =============================================================================
AZURE_STORAGE_ACCOUNT_NAME=cloudoptstorage2025
AZURE_STORAGE_ACCOUNT_KEY=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==
AZURE_CONTAINER_NAME=files

# =============================================================================
# TWILIO SMS (OPTIONAL - for budget alerts)
# =============================================================================
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# =============================================================================
# REDIS (For Celery - Local Development)
# =============================================================================
REDIS_URL=redis://localhost:6379/0

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
ENVIRONMENT=development
DEBUG=true
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

---

### Step 3: Generate Secure SECRET_KEY

**Run this to generate a random secret key:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Example output:**
```
xK3j9P2mN7qR5tY8wV1cF4gH6dJ0sL9aB2eN5pM8rQ3tX7yZ0wC4vF9gK2jN6mP8
```

**Copy this value** and replace `SECRET_KEY` in `.env`

---

### Step 4: Secure Your `.env` File

```bash
chmod 600 .env
```

**Add to `.gitignore`** (should already be there):
```bash
echo ".env" >> .gitignore
echo "gcp-credentials.json" >> .gitignore
```

---

## TESTING CREDENTIALS

### Test 1: MongoDB Connection

```bash
cd backend
source .venv/bin/activate
python -c "from app.core.database import get_db; next(get_db().command('ping')); print('Connected to MongoDB')"
```

**Expected output:** `Connected to MongoDB`

---

### Test 2: AWS S3 Access

**Create test file:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
cat > test_aws.py << 'EOF'
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

bucket = os.getenv('S3_BUCKET_NAME')
print(f"Testing connection to bucket: {bucket}")

try:
    response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
    print("✓ Successfully connected to AWS S3")
    print(f"✓ Bucket: {bucket}")
except Exception as e:
    print(f"✗ Error: {e}")
EOF

python3 test_aws.py
```

---

### Test 3: GCP Access

**Create test file:**
```bash
cat > test_gcp.py << 'EOF'
from google.cloud import compute_v1
import os
from dotenv import load_dotenv

load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GCP_SERVICE_ACCOUNT_JSON_PATH')

try:
    client = compute_v1.InstancesClient()
    project = os.getenv('GCP_PROJECT_ID')
    zone = os.getenv('GCP_ZONE')
    
    print(f"Testing connection to GCP project: {project}")
    instances = client.list(project=project, zone=zone)
    print("✓ Successfully connected to GCP Compute Engine")
    print(f"✓ Project: {project}")
    print(f"✓ Zone: {zone}")
except Exception as e:
    print(f"✗ Error: {e}")
EOF

python3 test_gcp.py
```

---

### Test 4: Azure Blob Storage

**Create test file:**
```bash
cat > test_azure.py << 'EOF'
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

connection_string = (
    f"DefaultEndpointsProtocol=https;"
    f"AccountName={os.getenv('AZURE_STORAGE_ACCOUNT_NAME')};"
    f"AccountKey={os.getenv('AZURE_STORAGE_ACCOUNT_KEY')};"
    f"EndpointSuffix=core.windows.net"
)

try:
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container = os.getenv('AZURE_CONTAINER_NAME')
    container_client = blob_service.get_container_client(container)
    
    if container_client.exists():
        print("✓ Successfully connected to Azure Blob Storage")
        print(f"✓ Account: {os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}")
        print(f"✓ Container: {container}")
    else:
        print(f"✗ Container '{container}' does not exist")
except Exception as e:
    print(f"✗ Error: {e}")
EOF

python3 test_azure.py
```

---

### Test 5: Redis Connection

```bash
redis-cli ping
```

**Expected response:** `PONG`

**Check Redis info:**
```bash
redis-cli info server | grep redis_version
```

---

### Test 6: Start Backend Server

```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
uvicorn app.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test health endpoint:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status":"healthy"}
```

---

### Test 7: Start Celery Worker

**Open new terminal:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
celery -A app.celery_worker worker --loglevel=info
```

**Expected output:**
```
 -------------- celery@YourHostname v5.x.x
---- **** ----- 
--- * ***  * -- Darwin-23.x.x
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         app:0x...
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 8 (prefork)
-- ******* ---- .> task events: OFF

[tasks]
  . app.storage.tasks.check_and_tier_files
  . app.storage.tasks.scan_for_sensitive_files

[2025-11-19 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-11-19 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2025-11-19 10:00:00,000: INFO/MainProcess] mingle: all alone
[2025-11-19 10:00:00,000: INFO/MainProcess] celery@YourHostname ready.
```

---

### Test 8: Start Celery Beat (Scheduler)

**Open another terminal:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
celery -A app.celery_worker beat --loglevel=info
```

**Expected output:**
```
celery beat v5.x.x is starting.
__    -    ... __   -        _
LocalTime -> 2025-11-19 10:00:00
Configuration ->
    . broker -> redis://localhost:6379/0
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> celerybeat-schedule
    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 minutes (300s)
```

---

### Test 9: Start Frontend

```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/frontend
npm run dev
```

**Visit:** http://localhost:5173/

---

## TROUBLESHOOTING

### Problem: AWS Access Denied Error

**Error:**
```
botocore.exceptions.ClientError: An error occurred (AccessDenied)
```

**Solutions:**
1. **Check IAM permissions:** Ensure policies are attached
2. **Verify credentials:** Make sure Access Key ID and Secret are correct
3. **Check region:** Ensure `PRIMARY_S3_REGION` matches bucket region
4. **Test with AWS CLI:**
   ```bash
   aws s3 ls s3://your-bucket-name --profile default
   ```

---

### Problem: GCP Authentication Failed

**Error:**
```
google.auth.exceptions.DefaultCredentialsError
```

**Solutions:**
1. **Check file path:** Ensure `GCP_SERVICE_ACCOUNT_JSON_PATH` is absolute path
2. **Verify file exists:**
   ```bash
   ls -la /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json
   ```
3. **Check permissions:**
   ```bash
   chmod 600 /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend/gcp-credentials.json
   ```
4. **Verify JSON format:** Open file and check for valid JSON

---

### Problem: Azure Connection Error

**Error:**
```
azure.core.exceptions.ClientAuthenticationError
```

**Solutions:**
1. **Regenerate key:** Go to Azure Portal → Storage Account → Access Keys → Regenerate key1
2. **Check account name:** Must be lowercase, no special characters
3. **Verify container exists:** Check in Azure Portal
4. **Test connection string:** Use Azure Storage Explorer app

---

### Problem: MongoDB Connection Timeout

**Error:**
```
pymongo.errors.ServerSelectionTimeoutError
```

**Solutions:**
1. **Check IP whitelist:** Ensure 0.0.0.0/0 is added or your current IP
2. **Verify password:** No special characters that need URL encoding
3. **Check connection string format:**
   ```
   mongodb+srv://username:password@cluster.mongodb.net/
   ```
4. **Test with MongoDB Compass:** Use GUI to verify connection

---

### Problem: "Module not found" Errors

**Solution:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
pip install -r requirements.txt
```

---

### Problem: Port Already in Use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)

# Restart server
uvicorn app.main:app --reload
```

---

### Problem: Redis Connection Refused

**Error:**
```
celery.exceptions.ImproperlyConfigured: Error connecting to Redis
```

**Solutions:**
1. **Check if Redis is running:**
   ```bash
   redis-cli ping
   ```
   
2. **Start Redis if not running:**
   ```bash
   brew services start redis
   ```
   
3. **Check Redis port:**
   ```bash
   lsof -i :6379
   ```
   
4. **Verify REDIS_URL in .env:**
   ```
   REDIS_URL=redis://localhost:6379/0
   ```

---

### Problem: Celery Worker Won't Start

**Error:**
```
ModuleNotFoundError: No module named 'app.celery_worker'
```

**Solutions:**
1. **Ensure you're in backend directory:**
   ```bash
   cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
   ```

2. **Check Python path:**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend"
   ```

3. **Verify celery_worker.py exists:**
   ```bash
   ls -la app/celery_worker.py
   ```

---

### Problem: Celery Tasks Not Executing

**Symptoms:**
- Tasks stay in PENDING state
- No task output in Celery worker logs

**Solutions:**
1. **Ensure Celery worker is running:**
   ```bash
   # Check worker logs for "ready" message
   celery -A app.celery_worker worker --loglevel=info
   ```

2. **Check task routing:**
   ```python
   # In celery_worker.py
   celery_app.conf.task_routes = {
       'app.storage.tasks.*': {'queue': 'storage'},
   }
   ```

3. **Flush Redis queue:**
   ```bash
   redis-cli FLUSHALL
   ```

4. **Restart worker and beat:**
   ```bash
   # Kill all Celery processes
   pkill -f 'celery worker'
   pkill -f 'celery beat'
   
   # Restart
   celery -A app.celery_worker worker --loglevel=info &
   celery -A app.celery_worker beat --loglevel=info &
   ```

---

## VERIFICATION CHECKLIST

After completing all steps, verify:

### Cloud Providers
- [ ] AWS S3 buckets created and accessible
- [ ] AWS Cost Explorer enabled (may take 24 hours)
- [ ] GCP project created with correct APIs enabled
- [ ] GCP service account JSON file downloaded and secured
- [ ] GCP Compute Engine zone set to free-tier eligible region
- [ ] Azure storage account created with container

### Infrastructure
- [ ] MongoDB Atlas cluster created and network access configured
- [ ] Redis installed and running locally
- [ ] Redis responds to `redis-cli ping` with `PONG`

### Configuration
- [ ] All credentials added to `.env` file
- [ ] SECRET_KEY generated and added
- [ ] `.env` file permissions set to 600
- [ ] `gcp-credentials.json` file secured with 600 permissions

### Application Services
- [ ] Backend starts without errors (`uvicorn app.main:app --reload`)
- [ ] Celery worker starts and shows "ready" message
- [ ] Celery beat starts and shows scheduler configuration
- [ ] Frontend connects to backend successfully

### Functionality Tests
- [ ] Can register new user account
- [ ] Can login successfully
- [ ] Dashboard loads with stats
- [ ] Can upload file to storage
- [ ] Can request VM (GCP)
- [ ] Budget alerts configured (if Twilio enabled)

---

## COST MONITORING

**To stay within free tier limits:**

### AWS
- **Monitor:** AWS Console → Billing Dashboard
- **Set alerts:** CloudWatch Billing Alarms
- **Free tier usage:** https://console.aws.amazon.com/billing/home#/freetier

### GCP
- **Monitor:** https://console.cloud.google.com/billing
- **Set budget alerts:** Billing → Budgets & alerts
- **Free tier:** First $300 credit lasts 90 days

### Azure
- **Monitor:** Cost Management + Billing → Cost analysis
- **Set budget:** Budgets → Create
- **Free tier:** $200 credit for 30 days

---

## SECURITY BEST PRACTICES

1. **Never commit credentials to Git:**
   ```bash
   git status  # Ensure .env is not staged
   ```

2. **Rotate credentials regularly:**
   - AWS: Every 90 days
   - GCP: Every 90 days
   - Azure: Every 90 days

3. **Use principle of least privilege:**
   - Only grant necessary permissions
   - Separate dev and prod credentials

4. **Enable MFA:**
   - AWS root account
   - GCP project owner account
   - Azure subscription owner

5. **Monitor unusual activity:**
   - Check billing daily
   - Review access logs weekly

---

## RUNNING THE FULL STACK

### Option 1: Quick Start Script (Recommended) ⭐

**Run ALL services in ONE terminal with unified logs:**

```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform
./start_all.sh
```

**Benefits:**
- ✅ Single terminal for everything
- ✅ Color-coded logs (easy to identify which service)
- ✅ See errors from all services in real-time
- ✅ Automatic Redis check and startup
- ✅ Health checks for each service
- ✅ Press `Ctrl+C` once to stop everything cleanly
- ✅ Logs saved to `logs/` directory for later review

**To stop all services:** Press `Ctrl+C` in the terminal

---

### Option 2: Manual Startup (5 Terminals)

**If you prefer separate terminals for each service:**

### Terminal 1: Redis (Background)
```bash
# Start Redis as background service
brew services start redis

# Verify
redis-cli ping
```

---

### Terminal 2: Backend API
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
source venv/bin/activate  # If using virtual environment
uvicorn app.main:app --reload
```

**Keep this terminal open** - Backend runs on http://localhost:8000

---

### Terminal 3: Celery Worker
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
source venv/bin/activate  # If using virtual environment
celery -A app.celery_worker worker --loglevel=info
```

**Keep this terminal open** - Processes background tasks

---

### Terminal 4: Celery Beat (Scheduler)
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend
source venv/bin/activate  # If using virtual environment
celery -A app.celery_worker beat --loglevel=info
```

**Keep this terminal open** - Schedules periodic tasks (budget checks, file tiering)

---

### Terminal 5: Frontend
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/frontend
npm run dev
```

**Keep this terminal open** - Frontend runs on http://localhost:5173

---

### Quick Start Script (Recommended)

**This script runs ALL services in ONE terminal with unified logs!**

**Create startup script:**
```bash
cd /Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform
cat > start_all.sh << 'EOF'
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Log file paths
LOG_DIR="logs"
mkdir -p $LOG_DIR
BACKEND_LOG="$LOG_DIR/backend.log"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker.log"
CELERY_BEAT_LOG="$LOG_DIR/celery_beat.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Clear old logs
> $BACKEND_LOG
> $CELERY_WORKER_LOG
> $CELERY_BEAT_LOG
> $FRONTEND_LOG

# Function to tail logs with prefix
tail_with_prefix() {
    local log_file=$1
    local prefix=$2
    local color=$3
    tail -f "$log_file" 2>/dev/null | while IFS= read -r line; do
        echo -e "${color}[${prefix}]${NC} $line"
    done &
}

# Cleanup function
cleanup() {
    echo -e "\n${RED}🛑 Shutting down all services...${NC}"
    
    # Kill all child processes
    pkill -P $$
    
    # Stop specific services
    echo -e "${YELLOW}Stopping Backend API...${NC}"
    kill $BACKEND_PID 2>/dev/null
    
    echo -e "${YELLOW}Stopping Celery Worker...${NC}"
    kill $WORKER_PID 2>/dev/null
    
    echo -e "${YELLOW}Stopping Celery Beat...${NC}"
    kill $BEAT_PID 2>/dev/null
    
    echo -e "${YELLOW}Stopping Frontend...${NC}"
    kill $FRONTEND_PID 2>/dev/null
    
    # Stop Redis if it was started by this script
    # echo -e "${YELLOW}Stopping Redis...${NC}"
    # brew services stop redis
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM EXIT

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Cloud Resource Optimization Platform - Start All        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Redis is running
echo -e "${BLUE}🔍 Checking Redis status...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Redis not running. Starting Redis...${NC}"
    brew services start redis
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Redis. Please check your installation.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Redis is already running${NC}"
fi

echo ""
echo -e "${BLUE}🚀 Starting all services...${NC}"
echo ""

# Start Backend API
echo -e "${GREEN}[1/4] Starting Backend API (port 8000)...${NC}"
cd backend
uvicorn app.main:app --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
sleep 2

# Check if backend started successfully
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Backend API started (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Backend API failed to start. Check logs: $BACKEND_LOG${NC}"
    exit 1
fi

# Start Celery Worker
echo -e "${GREEN}[2/4] Starting Celery Worker...${NC}"
celery -A app.celery_worker worker --loglevel=info > "$CELERY_WORKER_LOG" 2>&1 &
WORKER_PID=$!
sleep 2

# Check if celery worker started successfully
if ps -p $WORKER_PID > /dev/null; then
    echo -e "${GREEN}✅ Celery Worker started (PID: $WORKER_PID)${NC}"
else
    echo -e "${RED}❌ Celery Worker failed to start. Check logs: $CELERY_WORKER_LOG${NC}"
    exit 1
fi

# Start Celery Beat
echo -e "${GREEN}[3/4] Starting Celery Beat (Scheduler)...${NC}"
celery -A app.celery_worker beat --loglevel=info > "$CELERY_BEAT_LOG" 2>&1 &
BEAT_PID=$!
sleep 2

# Check if celery beat started successfully
if ps -p $BEAT_PID > /dev/null; then
    echo -e "${GREEN}✅ Celery Beat started (PID: $BEAT_PID)${NC}"
else
    echo -e "${RED}❌ Celery Beat failed to start. Check logs: $CELERY_BEAT_LOG${NC}"
    exit 1
fi

# Start Frontend
echo -e "${GREEN}[4/4] Starting Frontend (port 5173)...${NC}"
cd ../frontend
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 3

# Check if frontend started successfully
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}❌ Frontend failed to start. Check logs: $FRONTEND_LOG${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   All Services Started Successfully! 🎉                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${MAGENTA}📍 Service URLs:${NC}"
echo -e "   ${BLUE}Backend API:${NC}     http://localhost:8000"
echo -e "   ${BLUE}API Docs:${NC}        http://localhost:8000/docs"
echo -e "   ${BLUE}Frontend:${NC}        http://localhost:5173"
echo ""
echo -e "${MAGENTA}📝 Log Files:${NC}"
echo -e "   ${YELLOW}Backend:${NC}         $BACKEND_LOG"
echo -e "   ${YELLOW}Celery Worker:${NC}   $CELERY_WORKER_LOG"
echo -e "   ${YELLOW}Celery Beat:${NC}     $CELERY_BEAT_LOG"
echo -e "   ${YELLOW}Frontend:${NC}        $FRONTEND_LOG"
echo ""
echo -e "${MAGENTA}🔧 Process IDs:${NC}"
echo -e "   ${YELLOW}Backend:${NC}         $BACKEND_PID"
echo -e "   ${YELLOW}Celery Worker:${NC}   $WORKER_PID"
echo -e "   ${YELLOW}Celery Beat:${NC}     $BEAT_PID"
echo -e "   ${YELLOW}Frontend:${NC}        $FRONTEND_PID"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop all services):${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Start tailing logs with colored prefixes
tail_with_prefix "$BACKEND_LOG" "BACKEND" "$BLUE"
tail_with_prefix "$CELERY_WORKER_LOG" "CELERY-WORKER" "$YELLOW"
tail_with_prefix "$CELERY_BEAT_LOG" "CELERY-BEAT" "$MAGENTA"
tail_with_prefix "$FRONTEND_LOG" "FRONTEND" "$CYAN"

# Wait for all background processes
wait
EOF

chmod +x start_all.sh
```

**Run everything in ONE terminal:**
```bash
./start_all.sh
```

**What this script does:**

1. **✅ Checks Redis** - Starts it if not running
2. **✅ Starts all 4 services** - Backend, Celery Worker, Celery Beat, Frontend
3. **✅ Verifies each service** - Checks if PID exists, fails fast if error
4. **✅ Color-coded logs** - Each service has different color prefix:
   - 🔵 **[BACKEND]** - Blue
   - 🟡 **[CELERY-WORKER]** - Yellow
   - 🟣 **[CELERY-BEAT]** - Magenta
   - 🔷 **[FRONTEND]** - Cyan
5. **✅ Shows all info** - URLs, PIDs, log file locations
6. **✅ Unified error detection** - See errors from any service instantly
7. **✅ Clean shutdown** - Press `Ctrl+C` once to stop ALL services

**Example output:**
```
╔════════════════════════════════════════════════════════════╗
║   Cloud Resource Optimization Platform - Start All        ║
╚════════════════════════════════════════════════════════════╝

🔍 Checking Redis status...
✅ Redis is already running

🚀 Starting all services...

[1/4] Starting Backend API (port 8000)...
✅ Backend API started (PID: 12345)
[2/4] Starting Celery Worker...
✅ Celery Worker started (PID: 12346)
[3/4] Starting Celery Beat (Scheduler)...
✅ Celery Beat started (PID: 12347)
[4/4] Starting Frontend (port 5173)...
✅ Frontend started (PID: 12348)

╔════════════════════════════════════════════════════════════╗
║   All Services Started Successfully! 🎉                   ║
╚════════════════════════════════════════════════════════════╝

📍 Service URLs:
   Backend API:     http://localhost:8000
   API Docs:        http://localhost:8000/docs
   Frontend:        http://localhost:5173

📊 Live Logs (Ctrl+C to stop all services):
═══════════════════════════════════════════════════════════

[BACKEND] INFO:     Uvicorn running on http://127.0.0.1:8000
[CELERY-WORKER] celery@MacBook ready.
[FRONTEND] VITE v5.0.0 ready in 543 ms
[CELERY-BEAT] Scheduler: Sending due task...
```

---

### Alternative: View Logs in Separate Terminal (Optional)

**If script is running, you can view specific logs:**
```bash
# Watch backend logs only
tail -f logs/backend.log

# Watch celery worker logs only
tail -f logs/celery_worker.log

# View all errors across all logs
grep -i "error" logs/*.log
```

---

## NEXT STEPS

Once all credentials are configured:

1. **Test each feature:**
   - ✓ User registration/login
   - ✓ File upload to each cloud provider
   - ✓ VM request and assignment
   - ✓ Cost tracking dashboard
   - ✓ Budget alerts (requires Celery + Twilio)
   - ✓ Storage tiering (background task via Celery)

2. **Create sample data:**
   - Upload test files
   - Request test VMs
   - Set up budgets

3. **Verify background tasks:**
   ```bash
   # Check Celery tasks in Redis
   redis-cli KEYS "celery-task-meta-*"
   
   # Monitor task execution
   # Watch Celery worker terminal for task logs
   ```

4. **Backup configuration:**
   ```bash
   cp .env .env.production
   # Store securely outside project directory
   ```

5. **Document your setup:**
   - Note any deviations from this guide
   - Record any troubleshooting steps

---

## SUPPORT RESOURCES

### Official Documentation
- **AWS:** https://docs.aws.amazon.com/
- **GCP:** https://cloud.google.com/docs
- **Azure:** https://docs.microsoft.com/azure
- **MongoDB Atlas:** https://docs.atlas.mongodb.com/

### Free Tier Documentation
- **AWS Free Tier:** https://aws.amazon.com/free/
- **GCP Free Tier:** https://cloud.google.com/free
- **Azure Free Account:** https://azure.microsoft.com/free/

---

**Setup Complete!** 🎉

Your Cloud Resource Optimization Platform should now be fully operational with new credentials.

**Estimated Setup Time:** 2-3 hours  
**Estimated Monthly Cost (Free Tier):** $0.00  
**Credentials Expiration:** Monitor your free tier expiration dates

---

**Document Version:** 1.0  
**Last Updated:** November 19, 2025  
**Next Review:** When credentials expire or every 90 days
