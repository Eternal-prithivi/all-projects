# 🚀 Production Deployment Guide

## Overview
Deploy your Cloud Resource Optimization Platform to production with your Namecheap domain.

## 📋 Prerequisites
- ✅ GitHub Student Developer Pack (for free credits)
- ✅ Namecheap domain (from student pack)
- ✅ GitHub repository
- ✅ MongoDB Atlas account (free tier)
- ✅ Cloud credentials (AWS, GCP, Azure)

---

## 🎯 **Recommended Deployment Architecture**

```
yourdomain.com (Frontend - Vercel)
    ↓
api.yourdomain.com (Backend - Railway)
    ↓
MongoDB Atlas (Database - Free Tier)
Redis Cloud (Cache - Free Tier)
```

**Total Cost: $0-5/month** (within free tiers + student credits)

---

## Step 1: Prepare Your Code for Production

### 1.1 Update Environment Variables

Create `backend/.env.production`:

```env
# Environment
ENVIRONMENT=production
DEMO_MODE=false

# URLs (UPDATE THESE WITH YOUR DOMAIN)
FRONTEND_URL=https://yourdomain.com
BACKEND_URL=https://api.yourdomain.com

# MongoDB Atlas (Free Tier)
MONGO_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DB_NAME=zenith_production

# JWT (Generate new secret for production!)
SECRET_KEY=your-production-jwt-secret-generate-with-openssl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis Cloud (Free Tier)
CELERY_BROKER_URL=rediss://default:password@redis-xxxxx.cloud.redislabs.com:xxxxx
REDIS_URL=rediss://default:password@redis-xxxxx.cloud.redislabs.com:xxxxx

# Cloud Credentials (same as dev)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
GCP_PROJECT_ID=your-gcp-project
GCP_SERVICE_ACCOUNT_JSON_PATH=/app/gcp-key.json
AZURE_STORAGE_ACCOUNT_NAME=your_azure_account
AZURE_STORAGE_ACCOUNT_KEY=your_azure_key

# Other settings...
```

### 1.2 Update Frontend API URL

Edit `frontend/src/api.js`:

```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.PROD 
    ? 'https://api.yourdomain.com'  // Production
    : 'http://localhost:8000'        // Development
  );
```

Create `frontend/.env.production`:

```env
VITE_API_URL=https://api.yourdomain.com
```

---

## Step 2: Deploy Backend to Railway

### 2.1 Sign Up for Railway
1. Go to https://railway.app
2. Sign up with GitHub
3. Get $5/month free credit

### 2.2 Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your repository
4. Select "Deploy from Dockerfile"

### 2.3 Configure Railway

Create `backend/Dockerfile` (if not exists):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 2.4 Add Environment Variables in Railway
1. Go to your project → Variables
2. Copy ALL variables from `.env.production`
3. Add them one by one

### 2.5 Deploy
1. Railway will auto-deploy
2. Get your URL: `https://your-app.up.railway.app`
3. Test: `https://your-app.up.railway.app/health`

---

## Step 3: Deploy Frontend to Vercel

### 3.1 Sign Up for Vercel
1. Go to https://vercel.com
2. Sign up with GitHub
3. Free tier (perfect for React apps)

### 3.2 Import Project
1. Click "New Project"
2. Import your GitHub repo
3. Configure:
   - Framework: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

### 3.3 Add Environment Variables
1. Go to Settings → Environment Variables
2. Add:
   ```
   VITE_API_URL=https://your-app.up.railway.app
   ```

### 3.4 Deploy
1. Click "Deploy"
2. Get your URL: `https://your-project.vercel.app`

---

## Step 4: Configure Your Domain (Namecheap)

### 4.1 Add DNS Records in Namecheap

1. **Login to Namecheap** → Domain List → Manage → Advanced DNS

2. **Add Records:**

```
Type    Host    Value                           TTL
------------------------------------------------------
CNAME   @       cname.vercel-dns.com            Automatic
CNAME   api     your-app.up.railway.app         Automatic
CNAME   www     cname.vercel-dns.com            Automatic
```

### 4.2 Configure Custom Domain in Vercel

1. Go to Vercel → Project Settings → Domains
2. Add domain: `yourdomain.com`
3. Add domain: `www.yourdomain.com`
4. Vercel will verify DNS (wait 1-5 minutes)
5. Auto SSL certificate provisioned

### 4.3 Configure Custom Domain in Railway

1. Go to Railway → Project → Settings → Domains
2. Add custom domain: `api.yourdomain.com`
3. Follow verification steps
4. SSL auto-provisioned

### 4.4 Verify Setup

Wait 5-10 minutes for DNS propagation, then test:

```bash
# Frontend
curl https://yourdomain.com
# Should show React app

# Backend
curl https://api.yourdomain.com/health
# Should return: {"status": "healthy", ...}
```

---

## Step 5: Setup MongoDB Atlas (Free Tier)

### 5.1 Create Cluster
1. Go to https://mongodb.com/cloud/atlas
2. Sign up (free tier: 512MB storage)
3. Create cluster (choose AWS, closest region)

### 5.2 Configure Access
1. Database Access → Add User (username/password)
2. Network Access → Add IP: `0.0.0.0/0` (allow all - for Railway)

### 5.3 Get Connection String
1. Cluster → Connect → Connect your application
2. Copy connection string:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/zenith_production
   ```
3. Add to Railway environment variables: `MONGO_CONNECTION_STRING`

---

## Step 6: Setup Redis Cloud (Free Tier)

### 6.1 Create Database
1. Go to https://redis.com/try-free/
2. Sign up (free tier: 30MB)
3. Create database

### 6.2 Get Connection String
1. Database → Configuration
2. Copy endpoint: `redis-xxxxx.cloud.redislabs.com:xxxxx`
3. Copy password

### 6.3 Add to Railway
```
REDIS_URL=rediss://default:password@redis-xxxxx.cloud.redislabs.com:xxxxx
CELERY_BROKER_URL=rediss://default:password@redis-xxxxx.cloud.redislabs.com:xxxxx
```

---

## Step 7: Deploy Celery Worker (Railway)

### 7.1 Create Separate Service
1. Railway → New Service → Empty Service
2. Connect same GitHub repo
3. Name: "zenith-celery-worker"

### 7.2 Configure Worker

Create `backend/Dockerfile.worker`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start Celery worker
CMD ["celery", "-A", "app.celery_worker", "worker", "--loglevel=info"]
```

### 7.3 Add Environment Variables
- Copy same variables from main backend service
- Deploy

---

## Step 8: Production Checklist

### Security
- [ ] Change `DEMO_MODE=false` in production
- [ ] Generate new JWT secret: `openssl rand -hex 32`
- [ ] Update CORS to specific domain (not `*`)
- [ ] Add rate limiting (optional)
- [ ] Enable HTTPS everywhere
- [ ] Set up monitoring (Railway logs)

### Performance
- [ ] Enable caching (already implemented)
- [ ] Set cache TTL to 2-4 hours in production
- [ ] Monitor API costs (AWS billing alerts)
- [ ] Set up CDN for static files (Vercel handles this)

### Database
- [ ] Backup MongoDB Atlas regularly
- [ ] Create indexes for frequently queried fields
- [ ] Monitor database size (free tier: 512MB limit)

### Monitoring
- [ ] Set up error tracking (Sentry free tier)
- [ ] Monitor Railway logs
- [ ] Set up uptime monitoring (UptimeRobot free tier)
- [ ] AWS CloudWatch for cost alerts

---

## Step 9: Access Your Production App

1. **Frontend:** https://yourdomain.com
2. **Backend API:** https://api.yourdomain.com
3. **API Docs:** https://api.yourdomain.com/docs

---

## 🎯 **Cost Breakdown**

| Service | Free Tier | Estimated Cost |
|---------|-----------|----------------|
| Vercel (Frontend) | Unlimited | $0 |
| Railway (Backend) | $5 credit/month | $0-5 |
| MongoDB Atlas | 512MB | $0 |
| Redis Cloud | 30MB | $0 |
| Namecheap Domain | 1 year free (student) | $0 |
| AWS/GCP/Azure APIs | With caching | $1-2/month |
| **TOTAL** | | **$1-7/month** |

With GitHub Student Pack credits: **Effectively $0** for first year!

---

## 📝 **Post-Deployment**

### Update Your README
```markdown
## 🌐 Live Demo
- **Website:** https://yourdomain.com
- **API Documentation:** https://api.yourdomain.com/docs

## 🚀 Tech Stack
- Frontend: React 19 + Vite (Vercel)
- Backend: FastAPI + Python (Railway)
- Database: MongoDB Atlas
- Cache: Redis Cloud
- Cloud: AWS, GCP, Azure
```

### Share Your Project
- Add to portfolio
- Share on LinkedIn
- Include in resume
- GitHub README with live demo link

---

## 🆘 Troubleshooting

**Issue: CORS errors**
- Update `FRONTEND_URL` in Railway environment variables
- Check CORS configuration in `main.py`

**Issue: MongoDB connection fails**
- Verify connection string
- Check IP whitelist (use `0.0.0.0/0`)
- Ensure password doesn't have special characters

**Issue: Domain not working**
- Wait 10-15 minutes for DNS propagation
- Check DNS records in Namecheap
- Verify domain added in Vercel/Railway

**Issue: API costs too high**
- Verify `DEMO_MODE=false` (but caching enabled)
- Check cache TTL (should be 1-4 hours)
- Monitor AWS Cost Explorer

---

## 🎉 Success!

Your app is now live at **https://yourdomain.com**!

Users can access it worldwide, and you have a professional portfolio project with:
- ✅ Custom domain
- ✅ HTTPS security
- ✅ Production-grade deployment
- ✅ Auto-scaling (Vercel + Railway)
- ✅ Free tier hosting
- ✅ Professional CI/CD

**Next Steps:**
1. Share your live demo link
2. Add to resume/portfolio
3. Monitor usage and costs
4. Collect user feedback
5. Iterate and improve!
