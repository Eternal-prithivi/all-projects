# 🚀 VM Cluster Management - Quick Reference Card

## Installation
```bash
cd backend
pip install google-cloud-compute google-cloud-monitoring google-auth pyotp
```

## Start Services
```bash
# Terminal 1: Backend
uvicorn app.main:app --reload

# Terminal 2: Celery Worker  
celery -A app.celery_worker worker --loglevel=info

# Terminal 3: Celery Beat
celery -A app.celery_worker beat --loglevel=info
```

## Essential API Calls

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Request VM
```bash
curl -X POST http://localhost:8000/api/vm/request \
  -H "Content-Type: application/json" \
  -d '{"workload_description": "Web app development", "priority_level": 1}'
```

### 3. Get My Assignment
```bash
curl http://localhost:8000/api/vm/my-assignment
```

### 4. Get VM Metrics
```bash
curl http://localhost:8000/api/vm/metrics/general-vm-1
```

### 5. Migrate VM
```bash
curl -X POST http://localhost:8000/api/vm/transfer \
  -H "Content-Type: application/json" \
  -d '{"target_cluster": "STORAGE"}'
```

### 6. Get Recommendations (Admin)
```bash
curl http://localhost:8000/api/vm/admin/recommendations?min_score=50
```

### 7. Cluster Health (Admin)
```bash
curl http://localhost:8000/api/vm/admin/cluster-metrics/GENERAL
```

### 8. Release VM
```bash
curl -X POST http://localhost:8000/api/vm/release
```

## MongoDB Queries

### Check Assignments
```javascript
mongosh
use zenith_db
db.vm_assignments.find({status: "ACTIVE"}).pretty()
```

### Check Metrics
```javascript
db.vm_metrics.find().sort({collected_at: -1}).limit(5).pretty()
```

### Simulate Inactive User (for auto-release testing)
```javascript
db.vm_assignments.updateOne(
  {user_id: "demo_user"},
  {$set: {last_active: new Date(Date.now() - 35*60*1000)}}
)
```

### Simulate High CPU (for recommendations)
```javascript
db.vm_metrics.insertMany([
  {
    vm_name: "general-vm-1",
    cpu_usage: 85.3,
    memory_usage: 72.1,
    active_users: 2,
    collected_at: new Date()
  },
  {
    vm_name: "general-vm-2",
    cpu_usage: 22.1,
    memory_usage: 35.2,
    active_users: 1,
    collected_at: new Date()
  }
])
```

## GCP Commands

### List VMs
```bash
gcloud compute instances list --project=YOUR_PROJECT_ID
```

### Start VM Manually
```bash
gcloud compute instances start general-vm-1 --zone=us-central1-a
```

### Stop VM Manually
```bash
gcloud compute instances stop general-vm-1 --zone=us-central1-a
```

## Celery Manual Tasks

### Collect Metrics Now
```python
from app.vm.tasks import collect_vm_metrics_task
collect_vm_metrics_task()
```

### Run Auto-Release Now
```python
from app.vm.tasks import auto_release_inactive_vms_task
auto_release_inactive_vms_task()
```

### Health Check Now
```python
from app.vm.tasks import cluster_health_check_task
cluster_health_check_task()
```

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt

# Check .env file
cat backend/.env | grep GCP
```

### Celery not running
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Kill existing workers
pkill -f celery

# Restart
celery -A app.celery_worker worker --loglevel=info
```

### Metrics return 0
**Wait 10 minutes after VM starts for GCP Monitoring to populate**

### No recommendations
**Insert fake high CPU metrics (see MongoDB section above)**

### VM won't start
```bash
# Check GCP quotas
gcloud compute project-info describe --project=YOUR_PROJECT_ID

# Verify VM exists
gcloud compute instances describe general-vm-1 --zone=us-central1-a
```

## File Structure
```
backend/app/vm/
├── models.py                    # Pydantic schemas (300 lines)
├── workload_analyzer.py         # Keyword matching (200 lines)
├── metrics_collector.py         # GCP Monitoring (350 lines)
├── migration_recommender.py     # AI scoring (400 lines)
├── manager.py                   # VM operations (450 lines)
├── routes_vm.py                 # API endpoints (550 lines)
└── tasks.py                     # Celery jobs (300 lines)
```

## Background Tasks Schedule
- **collect_vm_metrics**: Every 5 minutes
- **auto_release_inactive_vms**: Every 10 minutes
- **cluster_health_check**: Every 15 minutes
- **cleanup_old_metrics**: Daily at 12:30 AM UTC

## Cost Estimate (Free Tier)
- **4 VMs stopped only:** $5.84/month
- **4 VMs with auto-release:** $7.20/month (8 hrs/day avg)
- **4 VMs running 24/7:** $20.44/month ❌

## Key Constants
```python
MAX_USERS_PER_VM = 5
CPU_OVERLOAD_THRESHOLD = 70.0  # %
CPU_UNDERLOAD_THRESHOLD = 30.0  # %
INACTIVITY_TIMEOUT = 30  # minutes
METRICS_RETENTION = 7  # days
E2_MICRO_COST = 0.007  # USD/hour
```

## Documentation Links
- **API Reference:** `docs/VM_CLUSTER_API_REFERENCE.md`
- **Testing Guide:** `docs/VM_TESTING_GUIDE.md`
- **Implementation Summary:** `docs/VM_IMPLEMENTATION_SUMMARY.md`
- **Project Roadmap:** `docs/PROJECT_SUMMARY_AND_ROADMAP.md`

## Success Checklist
- [ ] Backend starts without errors
- [ ] Health check returns `{"mongo_connected": true}`
- [ ] Celery worker & beat running
- [ ] Request VM → Receive assignment <60s
- [ ] Get metrics → Returns CPU/RAM data
- [ ] Recommendations → Score >50 generated
- [ ] Migration → User moved successfully
- [ ] Auto-release → Inactive user released after 30 min

## Need Help?
1. Check logs (uvicorn/celery console)
2. Review `docs/VM_TESTING_GUIDE.md`
3. Verify GCP credentials: `cat backend/zenith-gcp-key.json`
4. Test MongoDB: `mongosh` → `show dbs`

---
**Version:** 1.0.0 | **Status:** ✅ Ready | **LOC:** 2,550+
