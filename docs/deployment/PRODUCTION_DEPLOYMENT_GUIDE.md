# 🚀 Production Deployment Guide
## Cloud Resource Optimization Platform

---

## 📋 **Pre-Deployment Checklist**

### **Critical Steps Before Going Live**

- [ ] Read this entire document
- [ ] Backup all data from MongoDB
- [ ] Test all features in staging environment
- [ ] Have rollback plan ready
- [ ] Set up monitoring and alerts
- [ ] Review security settings

---

## 🔧 **REQUIRED CONFIGURATION CHANGES**

### **1. Backend Environment Variables (.env)**

#### **On Render Dashboard → zenith-backend → Environment:**

```bash
# ============================================
# PRODUCTION MODE SETTINGS
# ============================================

# Disable Demo Mode (CRITICAL!)
DEMO_MODE=false

# Enable Real Metrics
USE_REAL_METRICS=true

# Set Production Environment
ENVIRONMENT=production

# Production URLs
FRONTEND_URL=https://rajverse.me
BACKEND_URL=https://zenith-backend-707i.onrender.com

# ============================================
# PAYMENT CONFIGURATION (CRITICAL!)
# ============================================

# Replace with LIVE Razorpay keys (NOT test keys!)
RAZORPAY_KEY_ID=rzp_live_YOUR_ACTUAL_KEY_ID
RAZORPAY_KEY_SECRET=YOUR_ACTUAL_LIVE_SECRET
RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET

# ============================================
# DATABASE (Keep existing)
# ============================================
MONGO_CONNECTION_STRING=your_atlas_connection_string
MONGO_DB_NAME=zenith_production

# ============================================
# JWT SECURITY
# ============================================
SECRET_KEY=your_production_secret_key_minimum_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# CLOUD PROVIDERS (PRODUCTION CREDENTIALS)
# ============================================

# AWS Production Credentials
AWS_ACCESS_KEY_ID=your_production_aws_key
AWS_SECRET_ACCESS_KEY=your_production_aws_secret
S3_BUCKET_NAME=your-production-bucket
PRIMARY_S3_REGION=ap-south-1
REGULAR_S3_BUCKET_NAME=zenith-regular-prod
SECURE_S3_BUCKET_NAME=zenith-secure-prod
REPLICA_S3_BUCKET_NAME=zenith-replica-prod
REPLICA_S3_REGION=us-east-1

# GCP Production Credentials
GCP_PROJECT_ID=your-production-project-id
GCP_SERVICE_ACCOUNT_JSON_PATH=/etc/secrets/gcp-service-account.json
GCP_BUCKET_NAME=zenith-gcp-prod
GCP_ZONE=us-central1-a

# Azure Production Credentials
AZURE_STORAGE_ACCOUNT_NAME=zenithprodaccount
AZURE_STORAGE_ACCOUNT_KEY=your_production_key
AZURE_CONTAINER_NAME=zenith-prod-container
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# ============================================
# VM CLUSTER LIMITS (Adjust for production)
# ============================================
PERFORMANCE_CLUSTER_MAX_VMS=10  # Increase from 2
STORAGE_CLUSTER_MAX_VMS=10      # Increase from 2
PERFORMANCE_VM_MACHINE_TYPE=n2-standard-2  # Upgrade from e2-micro
STORAGE_VM_MACHINE_TYPE=n2-standard-2      # Upgrade from e2-micro
STORAGE_VM_DISK_SIZE_GB=100                # Increase from 20GB

# ============================================
# CELERY (Background Tasks)
# ============================================
CELERY_BROKER_URL=your_redis_url_or_rabbitmq

# ============================================
# OPTIONAL: Twilio (SMS Notifications)
# ============================================
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
```

---

### **2. Frontend Configuration**

#### **File: `frontend/src/api.js`**

**Current (Development):**
```javascript
const API_BASE_URL = import.meta.env.MODE === 'production' 
  ? 'https://zenith-backend-707i.onrender.com/api'
  : 'http://localhost:8000/api';
```

✅ **Already correct!** - Auto-detects production mode

#### **File: `frontend/vercel.json`**

**Verify these settings:**
```json
{
  "buildCommand": "npm install && npm run build",
  "installCommand": "npm install --legacy-peer-deps",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    },
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "no-cache, no-store, must-revalidate"
        }
      ]
    }
  ]
}
```

✅ **Already configured!**

---

### **3. Razorpay Production Setup**

#### **Steps:**

1. **Login to Razorpay Dashboard:**
   - Go to: https://dashboard.razorpay.com

2. **Switch to Live Mode:**
   - Top left: Toggle from "Test Mode" to "Live Mode"

3. **Get Live API Keys:**
   - Settings → API Keys → Generate Live Keys
   - Copy `Key ID` (starts with `rzp_live_`)
   - Copy `Key Secret`

4. **Setup Webhooks:**
   - Settings → Webhooks → Add Endpoint
   - URL: `https://zenith-backend-707i.onrender.com/api/payments/webhook`
   - Events: Select all payment events
   - Copy Webhook Secret

5. **Update Render Environment:**
   - Add live keys to Render (NOT test keys!)

6. **Update Frontend:**
   - Razorpay automatically uses live mode when you use live keys
   - No frontend changes needed

---

### **4. Database Production Setup**

#### **MongoDB Atlas Configuration:**

1. **Create Production Database:**
   ```
   Database Name: zenith_production
   ```

2. **Set up IP Whitelist:**
   - Add Render's IP addresses
   - Or allow from anywhere (0.0.0.0/0) with strong passwords

3. **Enable Backup:**
   - Atlas → Backup → Enable continuous backup
   - Schedule daily snapshots

4. **Set up Monitoring:**
   - Enable Atlas Performance Advisor
   - Set up alerts for slow queries
   - Monitor connection pool

5. **Update Connection String:**
   ```bash
   MONGO_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/zenith_production?retryWrites=true&w=majority
   ```

---

### **5. Security Hardening**

#### **Backend Security (`backend/app/main.py`):**

**Update CORS settings:**

```python
# CURRENT (Development):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ TOO PERMISSIVE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PRODUCTION (Replace with):
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://rajverse.me",
        "https://www.rajverse.me",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)
```

#### **JWT Secret Key:**

**Generate strong secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update in Render:
```bash
SECRET_KEY=<generated_key_here>
```

#### **Rate Limiting (Add to backend):**

Create `backend/app/middleware/rate_limit.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# In main.py:
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On sensitive endpoints:
@router.post("/auth/token")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: Request, ...):
    ...
```

---

### **6. Monitoring & Logging**

#### **Set up Error Tracking:**

**Option 1: Sentry (Recommended)**

1. Sign up at https://sentry.io
2. Create new project for Python/FastAPI
3. Install:
   ```bash
   pip install sentry-sdk[fastapi]
   ```

4. Add to `backend/app/main.py`:
   ```python
   import sentry_sdk
   
   sentry_sdk.init(
       dsn="your_sentry_dsn",
       environment="production",
       traces_sample_rate=0.1,
   )
   ```

#### **Set up Uptime Monitoring:**

**Already configured! ✅**
- GitHub Actions keep-alive workflow active
- Also add UptimeRobot (free):
  1. https://uptimerobot.com
  2. Add monitor: `https://zenith-backend-707i.onrender.com/health`
  3. Interval: 5 minutes
  4. Email alerts on downtime

#### **Application Logs:**

**Render Dashboard:**
- Logs → Set retention to 7 days
- Download critical logs weekly

---

### **7. Performance Optimization**

#### **Enable CDN (Vercel):**

✅ **Already enabled** - Vercel has built-in CDN

#### **Database Indexing:**

**Run in MongoDB:**
```javascript
// Index for faster queries
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.vm_assignments.createIndex({ "user_id": 1, "vm_name": 1 });
db.vm_metrics.createIndex({ "vm_name": 1, "collected_at": -1 });
db.payment_orders.createIndex({ "user_id": 1, "created_at": -1 });
db.subscriptions.createIndex({ "user_id": 1, "status": 1 });
```

#### **Caching Strategy:**

✅ **Already implemented** but verify:
- VM Metrics: 2 min TTL
- Billing: 1 hour TTL
- Recommendations: 3 min TTL

---

### **8. Cost Management**

#### **Set up Cloud Budgets:**

**AWS:**
1. AWS Console → Billing → Budgets
2. Create budget: $50/month
3. Alert at 80% and 100%

**GCP:**
1. GCP Console → Billing → Budgets & alerts
2. Create budget: $50/month
3. Alert at 80% and 100%

**Azure:**
1. Azure Portal → Cost Management → Budgets
2. Create budget: $50/month
3. Alert at 80% and 100%

#### **Resource Cleanup:**

Schedule cleanup jobs:
```python
# Delete unused VMs after 7 days inactive
# Clean old metrics data (>30 days)
# Archive old payment records (>90 days)
```

---

### **9. Backup Strategy**

#### **MongoDB Backups:**
- ✅ Atlas automatic backups (every 24h)
- Manual backup before deployments

#### **Code Backups:**
- ✅ GitHub repository
- Tag releases: `git tag v1.0.0`

#### **Environment Backups:**
- Download `.env` and store securely
- Document all Render environment variables

---

### **10. Testing Checklist**

**Before deploying, test:**

- [ ] User registration & login
- [ ] 2FA enrollment and verification
- [ ] VM creation & deletion
- [ ] File upload to all providers (AWS/GCP/Azure)
- [ ] Cost analysis dashboard
- [ ] Payment flow with real test card
- [ ] Subscription upgrade/downgrade
- [ ] Password reset flow
- [ ] Session management
- [ ] API rate limiting
- [ ] Error handling
- [ ] Mobile responsiveness ([checklist](../testing/mobile_responsive_checklist.md))

---

## 🚀 **DEPLOYMENT SEQUENCE**

### **Step-by-Step Deployment:**

#### **Phase 1: Preparation (1-2 days)**

1. ✅ **Backup everything:**
   ```bash
   # Export current database
   mongodump --uri="your_connection_string"
   
   # Backup .env files
   cp backend/.env backend/.env.backup
   
   # Tag current version
   git tag v0.9-pre-production
   git push --tags
   ```

2. ✅ **Get production credentials:**
   - Razorpay live keys
   - AWS production IAM keys
   - GCP production service account
   - Azure production keys

3. ✅ **Create production database:**
   - New Atlas cluster or separate database
   - Name: `zenith_production`

#### **Phase 2: Backend Deployment (30 mins)**

1. **Update Render environment variables:**
   - Go to Render Dashboard
   - Select `zenith-backend` service
   - Environment tab
   - Update all variables from section 1 above
   - **Save Changes** (triggers automatic redeploy)

2. **Wait for deployment** (~5 minutes)

3. **Verify backend:**
   ```bash
   curl https://zenith-backend-707i.onrender.com/health
   # Should return: {"mongo_connected":true,"gcp_credentials_present":true}
   
   # Check it's NOT in demo mode:
   curl https://zenith-backend-707i.onrender.com/api/budgets/status \
     -H "Authorization: Bearer <test_token>"
   # Response should NOT have "demo_mode": true
   ```

#### **Phase 3: Frontend Deployment (10 mins)**

1. **Update production settings (if needed):**
   - ✅ Already configured in `api.js`
   - ✅ Already configured in `vercel.json`

2. **Deploy to Vercel:**
   ```bash
   git add .
   git commit -m "chore: Production-ready configuration"
   git push origin fresh-start
   ```

3. **Vercel auto-deploys** (~2 minutes)

4. **Verify frontend:**
   - Visit: https://rajverse.me
   - Check browser console for errors
   - Verify API calls go to production backend

#### **Phase 4: Post-Deployment Verification (30 mins)**

**Test critical flows:**

1. **Authentication:**
   - [ ] Register new account
   - [ ] Login with credentials
   - [ ] Enable 2FA
   - [ ] Logout and login with 2FA

2. **VM Operations:**
   - [ ] Request new VM
   - [ ] Check VM metrics
   - [ ] Release VM

3. **Storage:**
   - [ ] Upload file to AWS
   - [ ] Upload file to GCP
   - [ ] Upload file to Azure
   - [ ] Download files

4. **Payments (IMPORTANT - Use real test card):**
   - [ ] View pricing plans
   - [ ] Upgrade to paid plan
   - [ ] Complete payment with test card
   - [ ] Verify subscription updated
   - [ ] Check payment in Razorpay dashboard

5. **Billing:**
   - [ ] View current costs
   - [ ] Check billing breakdown
   - [ ] Verify total includes cloud + subscription

#### **Phase 5: Monitoring Setup (1 hour)**

1. **Set up alerts:**
   - [ ] Sentry error tracking
   - [ ] UptimeRobot monitoring
   - [ ] Cloud budget alerts
   - [ ] Database slow query alerts

2. **Document everything:**
   - [ ] Save all environment variables securely
   - [ ] Document deployment process
   - [ ] Create runbook for common issues

---

## 🔄 **ROLLBACK PLAN**

**If something goes wrong:**

### **Backend Rollback:**

1. **Render Dashboard:**
   - Go to Deployments
   - Find previous stable deployment
   - Click "Redeploy"

2. **Or revert environment:**
   - Change `DEMO_MODE=true`
   - Change `USE_REAL_METRICS=false`
   - Revert Razorpay to test keys

### **Frontend Rollback:**

1. **Vercel Dashboard:**
   - Deployments tab
   - Find previous deployment
   - Click "Promote to Production"

### **Database Rollback:**

1. **MongoDB Atlas:**
   - Backup → Snapshots
   - Restore previous snapshot

---

## 💰 **COST ESTIMATES (Production)**

### **Monthly Costs (Estimated):**

| Service | Free Tier | Paid Tier | Your Usage |
|---------|-----------|-----------|------------|
| **Render** | $0 (free tier) | $7/month | Free tier OK |
| **Vercel** | $0 (hobby) | $20/month | Free tier OK |
| **MongoDB Atlas** | $0 (512MB) | $9/month (2GB) | ~$0 (small) |
| **AWS (S3 + EC2)** | $0-5 | $10-50 | ~$5-10 |
| **GCP (VMs + Storage)** | $0-5 | $10-50 | ~$5-10 |
| **Azure (Storage)** | $0-2 | $5-20 | ~$2-5 |
| **Razorpay** | 2% per transaction | 2% per transaction | Variable |
| **Sentry** | $0 (5k events) | $26/month | Free tier OK |
| **GitHub Actions** | $0 (2000 min) | Free | $0 |

**Total Estimated: $10-30/month** (without user payments)

**With 100 paying users:**
- Revenue: ₹49,900/month (~$600)
- Cloud costs: ~$30-50
- **Profit margin: ~95%** 🎉

---

## ⚠️ **CRITICAL WARNINGS**

### **NEVER DO THIS:**

❌ **Don't commit secrets to Git:**
```bash
# Add to .gitignore:
.env
.env.production
*.pem
*.json  # GCP service account keys
```

❌ **Don't use test keys in production:**
- Always use `rzp_live_xxx` for Razorpay
- Never use development AWS/GCP keys

❌ **Don't expose sensitive data:**
- Never log passwords or API keys
- Sanitize error messages sent to frontend

❌ **Don't skip backups:**
- Backup database before major changes
- Keep weekly backups for 30 days

---

## 📞 **SUPPORT & MAINTENANCE**

### **Daily Tasks:**
- ✅ Check error logs (Sentry)
- ✅ Monitor uptime (UptimeRobot)
- ✅ Review costs (AWS/GCP/Azure)

### **Weekly Tasks:**
- ✅ Review user feedback
- ✅ Check database performance
- ✅ Update dependencies (security patches)
- ✅ Backup environment configs

### **Monthly Tasks:**
- ✅ Review and optimize costs
- ✅ Update documentation
- ✅ Security audit
- ✅ Performance review

---

## 🎯 **POST-DEPLOYMENT CHECKLIST**

After going live:

- [ ] All environment variables updated
- [ ] DEMO_MODE=false verified
- [ ] Razorpay live keys active
- [ ] CORS restricted to rajverse.me
- [ ] SSL certificates valid
- [ ] Database backups enabled
- [ ] Monitoring alerts configured
- [ ] Budget alerts set up
- [ ] Error tracking active
- [ ] Keep-alive workflow running
- [ ] All critical flows tested
- [ ] Documentation updated
- [ ] Team notified
- [ ] Rollback plan tested
- [ ] Support email configured

---

## 📚 **ADDITIONAL RESOURCES**

**Documentation:**
- Render: https://render.com/docs
- Vercel: https://vercel.com/docs
- MongoDB Atlas: https://docs.atlas.mongodb.com
- Razorpay: https://razorpay.com/docs

**Support:**
- Create issues in GitHub
- Check Render/Vercel status pages
- MongoDB support (paid plans)

---

## ✅ **FINAL VERIFICATION**

**Run this command after deployment:**

```bash
# Test production backend
curl https://zenith-backend-707i.onrender.com/health

# Expected: {"mongo_connected":true,"gcp_credentials_present":true}

# Test frontend
curl -I https://rajverse.me

# Expected: HTTP/2 200

# Verify NOT in demo mode (login first and get token):
curl https://zenith-backend-707i.onrender.com/api/dashboard/overview \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response should have real data, NOT demo_mode: true
```

---

## 🎉 **YOU'RE LIVE!**

Congratulations! Your Cloud Resource Optimization Platform is now production-ready!

**Next Steps:**
1. Monitor first 24 hours closely
2. Collect user feedback
3. Iterate and improve
4. Scale as needed

**Remember:**
- Start small, scale gradually
- Monitor costs closely
- Keep security updated
- Backup regularly

---

**Document Version:** 1.0  
**Last Updated:** November 30, 2025  
**Created by:** GitHub Copilot  
**For:** Cloud Resource Optimization Platform

