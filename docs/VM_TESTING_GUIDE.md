# VM Cluster Management - Quick Start Testing Guide

## Prerequisites
✅ 4 VMs created in GCP Console (general-vm-1, general-vm-2, storage-vm-1, storage-vm-2)  
✅ Backend dependencies installed (`pip install -r requirements.txt`)  
✅ MongoDB running  
✅ GCP credentials configured (`zenith-gcp-key.json`)  
✅ Redis running (for Celery)

---

## Step 1: Install New Dependencies
```bash
cd backend
pip install google-cloud-compute google-cloud-monitoring google-auth pyotp
```

---

## Step 2: Start Backend Server
```bash
# Terminal 1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Application startup complete.
GCP Credentials loaded from: /path/to/zenith-gcp-key.json
```

**Health Check:**
```bash
curl http://localhost:8000/health
# {"mongo_connected": true, "gcp_credentials_present": true}
```

---

## Step 3: Start Celery Workers (Background Tasks)
```bash
# Terminal 2: Celery Worker
celery -A app.celery_worker worker --loglevel=info

# Terminal 3: Celery Beat Scheduler
celery -A app.celery_worker beat --loglevel=info
```

**You should see:**
- Worker: "celery@hostname ready"
- Beat: Scheduler registering 5 tasks (collect_vm_metrics, auto_release_inactive_vms, etc.)

---

## Step 4: Test VM Assignment Flow

### 4.1 Request VM for Web Development
```bash
curl -X POST http://localhost:8000/api/vm/request \
  -H "Content-Type: application/json" \
  -d '{
    "workload_description": "Running a Node.js web application",
    "priority_level": 1
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "VM assigned successfully",
  "vm_name": "general-vm-1",
  "vm_ip": "34.XX.XX.XX",
  "ssh_command": "ssh user@34.XX.XX.XX",
  "cluster_type": "GENERAL"
}
```

**What Happened:**
1. Workload analyzer detected keywords: "node", "web" → Recommended GENERAL cluster
2. Manager checked both general VMs → Found all stopped
3. Started general-vm-1 (45-60 seconds startup time)
4. Created assignment in MongoDB
5. Returned SSH command

---

### 4.2 Request VM for Database Storage
```bash
curl -X POST http://localhost:8000/api/vm/request \
  -H "Content-Type: application/json" \
  -d '{
    "workload_description": "PostgreSQL database with 500GB data backup",
    "cluster_preference": "STORAGE",
    "priority_level": 1
  }'
```

**Expected Response:**
```json
{
  "vm_name": "storage-vm-1",
  "cluster_type": "STORAGE"
}
```

**What Happened:**
1. Keywords: "database", "backup" → Recommended STORAGE cluster
2. User preference matched recommendation
3. Started storage-vm-1
4. Load balancing: 0 users on both storage VMs → Assigned to storage-vm-1

---

### 4.3 Get Your Current Assignment
```bash
curl http://localhost:8000/api/vm/my-assignment
```

**Response:**
```json
{
  "assignment_id": "assign_abc123xyz",
  "user_id": "demo_user",
  "vm_name": "general-vm-1",
  "vm_ip": "34.XX.XX.XX",
  "cluster_type": "GENERAL",
  "workload_description": "Running a Node.js web application",
  "assigned_at": "2025-06-15T10:30:00Z",
  "last_active": "2025-06-15T10:30:00Z",
  "status": "ACTIVE"
}
```

---

## Step 5: Test Real-Time Metrics

### 5.1 Get VM Metrics
```bash
curl http://localhost:8000/api/vm/metrics/general-vm-1
```

**Note:** First request may return error if VM just started (metrics take 5-10 minutes to populate in GCP Monitoring API). Try again after 10 minutes.

**Expected Response:**
```json
{
  "vm_name": "general-vm-1",
  "cpu_usage": 12.3,
  "memory_usage": 28.5,
  "disk_io_mb": 45.2,
  "network_io_mb": 12.8,
  "active_users": 1,
  "uptime_hours": 0.5,
  "estimated_cost_usd": 0.0035,
  "status": "RUNNING"
}
```

---

### 5.2 Check Cluster Health (Admin)
```bash
curl http://localhost:8000/api/vm/admin/cluster-metrics/GENERAL
```

**Response:**
```json
{
  "cluster_type": "GENERAL",
  "total_vms": 2,
  "running_vms": 1,
  "total_active_users": 1,
  "average_cpu_usage": 12.3,
  "vms": [
    {
      "vm_name": "general-vm-1",
      "status": "RUNNING",
      "active_users": 1,
      "cpu_usage": 12.3
    },
    {
      "vm_name": "general-vm-2",
      "status": "STOPPED",
      "active_users": 0,
      "cpu_usage": 0
    }
  ]
}
```

---

## Step 6: Test Migration (Workload Transfer)

### 6.1 Simulate Second User (Manual)
Insert another assignment directly in MongoDB:
```bash
mongosh
use zenith_db
db.vm_assignments.insertOne({
  assignment_id: "assign_test2",
  user_id: "test_user_2",
  vm_name: "general-vm-1",
  vm_ip: "34.XX.XX.XX",
  cluster_type: "GENERAL",
  workload_description: "Test workload",
  priority_level: 2,
  assigned_at: new Date(),
  last_active: new Date(),
  status: "ACTIVE"
})
```

---

### 6.2 Migrate Your User to Another VM
```bash
curl -X POST http://localhost:8000/api/vm/transfer \
  -H "Content-Type: application/json" \
  -d '{"target_cluster": "GENERAL"}'
```

**Expected Response:**
```json
{
  "success": true,
  "source_vm": "general-vm-1",
  "target_vm": "general-vm-2",
  "target_ip": "34.YY.YY.YY",
  "source_vm_stopped": false,  // Still has test_user_2
  "ssh_command": "ssh user@34.YY.YY.YY"
}
```

**What Happened:**
1. Found your assignment on general-vm-1
2. Checked other general VMs for least connections
3. Started general-vm-2 (was stopped)
4. Updated your assignment to general-vm-2
5. Kept general-vm-1 running (test_user_2 still active)

---

## Step 7: Test AI Migration Recommendations

### 7.1 Simulate Overloaded VM
Insert fake high CPU metrics:
```bash
mongosh
use zenith_db
db.vm_metrics.insertOne({
  vm_name: "general-vm-1",
  cpu_usage: 85.3,
  memory_usage: 72.1,
  active_users: 1,
  collected_at: new Date()
})

db.vm_metrics.insertOne({
  vm_name: "general-vm-2",
  cpu_usage: 22.1,
  memory_usage: 35.2,
  active_users: 1,
  collected_at: new Date()
})
```

---

### 7.2 Get Recommendations
```bash
curl "http://localhost:8000/api/vm/admin/recommendations?min_score=60"
```

**Expected Response:**
```json
[
  {
    "recommendation_id": "rec_abc123",
    "action": "migrate_user",
    "user_id": "test_user_2",
    "source_vm": "general-vm-1",
    "target_vm": "general-vm-2",
    "score": 85,
    "reasons": [
      "Severe CPU imbalance: Source VM at 85.3%, Target at 22.1%",
      "Source VM overloaded at 85.3% CPU",
      "Target VM has available capacity (1/5 users, 22.1% CPU)"
    ],
    "expected_improvements": {
      "cpu_reduction_source": "85.3%",
      "performance_gain": "30-50% faster response times expected"
    },
    "confidence": 95
  }
]
```

**Scoring Breakdown:**
- CPU imbalance (85.3% - 22.1% = 63.2% diff): +35 points
- Source overload (85.3% > 70%): +25 points
- Target capacity (22.1% < 50%, 1 < 5 users): +15 points
- **Total: 75+ points** (High Priority)

---

## Step 8: Test Auto-Release (Wait 30 Min)

### 8.1 Simulate Inactivity
Update last_active timestamp to >30 minutes ago:
```bash
mongosh
use zenith_db
db.vm_assignments.updateOne(
  {user_id: "demo_user"},
  {$set: {last_active: new Date(Date.now() - 35*60*1000)}}  // 35 min ago
)
```

---

### 8.2 Wait for Celery Task (runs every 10 min)
Or manually trigger in Python console:
```python
from app.vm.tasks import auto_release_inactive_vms_task
auto_release_inactive_vms_task()
```

**Expected Logs:**
```
✓ Released demo_user from general-vm-2 (VM stopped - no remaining users)
Auto-release complete: 1 assignments released, 1 VMs stopped
```

---

### 8.3 Verify Assignment Released
```bash
curl http://localhost:8000/api/vm/my-assignment
# 404 - No active VM assignment found
```

---

## Step 9: Verify Background Metrics Collection

### 9.1 Check Celery Beat Logs (Terminal 3)
You should see every 5 minutes:
```
[2025-06-15 14:25:00] Scheduler: Sending due task collect_vm_metrics
```

### 9.2 Check MongoDB for Metrics
```bash
mongosh
use zenith_db
db.vm_metrics.find().sort({collected_at: -1}).limit(5).pretty()
```

**Expected:** 5 most recent metric documents, collected ~5 minutes apart

---

## Step 10: Test Release & Cost Savings

### 10.1 Release VM Manually
```bash
curl -X POST http://localhost:8000/api/vm/release
```

**Response:**
```json
{
  "success": true,
  "vm_name": "general-vm-1",
  "vm_stopped": true,
  "remaining_users": 0
}
```

---

### 10.2 Verify VM Stopped in GCP
```bash
gcloud compute instances list --project=YOUR_PROJECT_ID
```

**Expected:**
```
NAME            ZONE           STATUS
general-vm-1    us-central1-a  TERMINATED
general-vm-2    us-central1-a  TERMINATED
```

**Cost Savings:**
- Running: $0.007/hour
- Stopped: $0.002/hour (80% savings)

---

## Common Issues & Fixes

### Issue 1: "No active VM assignment found"
**Cause:** User doesn't have assignment  
**Fix:** Request VM first via `/api/vm/request`

---

### Issue 2: Metrics return 0.0 for CPU/RAM
**Cause:** VM just started, GCP Monitoring API has no data yet  
**Fix:** Wait 10-15 minutes, then query again. Celery task will collect metrics automatically.

---

### Issue 3: VM won't start
**Cause:** GCP quota limits or stopped VM doesn't exist  
**Fix:**
```bash
gcloud compute instances list --project=YOUR_PROJECT_ID
# Verify VM exists and zone matches settings.GCP_ZONE
```

---

### Issue 4: Celery tasks not running
**Cause:** Redis not running or worker/beat not started  
**Fix:**
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Restart Celery
pkill -f celery
celery -A app.celery_worker worker --loglevel=info &
celery -A app.celery_worker beat --loglevel=info &
```

---

### Issue 5: Recommendations empty
**Cause:** No load imbalance or all VMs stopped  
**Fix:** Insert fake metrics (Step 7.1) or run workload on VMs to generate real load

---

## Testing Checklist

- [ ] Backend health check passes
- [ ] Celery worker & beat running
- [ ] Request VM → Assignment successful
- [ ] Get my assignment → Returns data
- [ ] VM metrics → Returns CPU/RAM (after 10 min)
- [ ] Cluster health → Shows 1-2 running VMs
- [ ] Migration → Successfully moves user
- [ ] Recommendations → Returns scored suggestions (with fake data)
- [ ] Auto-release → Releases inactive user (after 30 min)
- [ ] Manual release → Stops VM with 0 users

---

## Next Steps: Frontend Integration

Once backend testing passes:
1. Create React dashboard with 3D VM visualization (Three.js)
2. Real-time metrics charts (Chart.js or Recharts)
3. Admin panel for recommendations
4. User portal for VM requests
5. WebSocket for live updates

---

## Performance Benchmarks (Expected)

| Operation | Time |
|-----------|------|
| Request VM (VM already running) | <2s |
| Request VM (start new VM) | 45-60s |
| Get assignment | <100ms |
| Get metrics | 1-3s (GCP API call) |
| Migration (workload transfer) | 15-30s |
| Auto-release check | <500ms per user |
| Metrics collection (4 VMs) | 5-10s |

---

## Free Tier Cost Estimate

**4 VMs (e2-micro) running 24/7:**
- Running: $0.007/hour × 4 × 730 hours = $20.44/month ❌

**4 VMs with auto-release (shared, 8 hours/day avg):**
- Running: $0.007/hour × 2 VMs × 8 hours × 30 days = $3.36/month
- Stopped: $0.002/hour × 4 VMs × 16 hours × 30 days = $3.84/month
- **Total: $7.20/month** ✅ (Well within $300 free credit)

**4 VMs stopped (storage only):**
- $0.002/hour × 4 × 730 hours = $5.84/month (snapshot storage)

---

## Success Metrics

✅ **Working Implementation:**
- User can request VM and receive assignment <60s
- Migration recommendations generate scores >50 for imbalanced loads
- Auto-release reduces VM runtime by 60-80%
- Metrics collected every 5 minutes without errors

✅ **Cost Optimization:**
- Average VM runtime <10 hours/day per VM
- Monthly cost <$10 with normal usage

✅ **Reliability:**
- 99%+ uptime for backend API
- <5% failed metrics collections
- Zero data loss in MongoDB

---

## Demo Presentation Script

1. **Show backend health:** "System connected to GCP and MongoDB ✅"
2. **Request VM:** "AI analyzes workload, assigns to optimal cluster"
3. **Show metrics:** "Real-time CPU, RAM, cost tracking"
4. **Simulate load:** "Insert fake high CPU, generate recommendations"
5. **Apply migration:** "User moved to less-loaded VM automatically"
6. **Auto-release demo:** "VM stops after 30 min inactivity, saving costs"
7. **Show MongoDB:** "All assignments and metrics logged for analytics"

---

## Support & Documentation

- **API Reference:** `docs/VM_CLUSTER_API_REFERENCE.md`
- **Project Summary:** `docs/PROJECT_SUMMARY_AND_ROADMAP.md`
- **GCP Setup:** `docs/setup_guide.md`
- **Logs:** Check `uvicorn` and `celery` console outputs

**Good luck with testing! 🚀**
