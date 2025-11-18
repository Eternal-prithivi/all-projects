# VM Cluster Management - API Reference

## Overview
The VM cluster management system provides intelligent workload assignment, auto-scaling, and predictive migration recommendations across 4 GCP VMs (2 general-purpose, 2 storage-optimized).

**Base URL:** `http://localhost:8000/api/vm`

---

## Authentication
All endpoints require JWT authentication (except legacy endpoints). Include token in header:
```
Authorization: Bearer <your_jwt_token>
```

For demo/testing, authentication is simplified and returns `demo_user`.

---

## Core Endpoints

### 1. Request VM Assignment
**POST** `/request`

Intelligently assigns user to optimal VM based on workload analysis.

**Request Body:**
```json
{
  "workload_description": "Running a PostgreSQL database with 500GB of data",
  "cluster_preference": "STORAGE",  // Optional: "GENERAL" or "STORAGE"
  "priority_level": 1  // 1=High, 2=Normal, 3=Low
}
```

**Response:**
```json
{
  "success": true,
  "message": "VM assigned successfully",
  "vm_name": "storage-vm-1",
  "vm_ip": "34.123.45.67",
  "ssh_command": "ssh user@34.123.45.67",
  "cluster_type": "STORAGE"
}
```

**Use Cases:**
- Student requests VM for web development → Auto-assigned to general cluster
- User needs storage for database → Auto-assigned to storage cluster
- Workload description analyzed via keyword matching (70+ keywords)

---

### 2. Get My VM Assignment
**GET** `/my-assignment`

Retrieve current active VM assignment for authenticated user.

**Response:**
```json
{
  "assignment_id": "assign_a1b2c3d4e5f6",
  "user_id": "demo_user",
  "vm_name": "general-vm-2",
  "vm_ip": "34.67.89.12",
  "cluster_type": "GENERAL",
  "workload_description": "Web app development",
  "priority_level": 1,
  "assigned_at": "2025-06-15T10:30:00Z",
  "last_active": "2025-06-15T14:22:00Z",
  "status": "ACTIVE",
  "recommendation_confidence": 85
}
```

---

### 3. Transfer/Migrate VM
**POST** `/transfer`

User-initiated or admin-forced migration to another VM.

**Request Body (Auto-selection):**
```json
{
  "target_cluster": "STORAGE"  // System auto-selects least-loaded VM
}
```

**Request Body (Manual):**
```json
{
  "target_vm_name": "storage-vm-2"  // Directly specify target VM
}
```

**Response:**
```json
{
  "success": true,
  "source_vm": "general-vm-1",
  "target_vm": "storage-vm-2",
  "target_ip": "34.56.78.90",
  "source_vm_stopped": true,  // Stopped if no other users
  "ssh_command": "ssh user@34.56.78.90"
}
```

**Migration Process:**
1. Start target VM if stopped
2. Update user assignment in MongoDB
3. Stop source VM if no remaining users (cost savings)

---

### 4. Release VM Assignment
**POST** `/release`

Release current VM assignment. VM auto-stops if no users remain.

**Response:**
```json
{
  "success": true,
  "vm_name": "general-vm-1",
  "vm_stopped": true,
  "remaining_users": 0
}
```

**Auto-Release:**
- Celery task runs every 10 minutes
- Releases assignments inactive > 30 minutes
- Stops VMs with 0 users to save costs

---

### 5. Get VM Metrics
**GET** `/metrics/{vm_name}`

Fetch real-time performance metrics from GCP Monitoring API.

**Example:** `GET /metrics/general-vm-1`

**Response:**
```json
{
  "vm_name": "general-vm-1",
  "cpu_usage": 45.3,  // Percentage
  "memory_usage": 62.1,  // Percentage
  "disk_io_mb": 124.5,
  "network_io_mb": 87.3,
  "active_users": 2,
  "uptime_hours": 18.5,
  "estimated_cost_usd": 0.1295,  // $0.007/hour * 18.5 hours
  "status": "RUNNING",
  "timestamp": "2025-06-15T14:25:00Z"
}
```

**Metrics Source:**
- CPU: `compute.googleapis.com/instance/cpu/utilization`
- Memory: `agent.googleapis.com/memory/percent_used` (requires monitoring agent)
- Disk/Network: GCP API read/write byte counters

---

## Admin Endpoints

### 6. Get Migration Recommendations
**GET** `/admin/recommendations?cluster_type=GENERAL&min_score=50`

AI-powered migration suggestions based on real-time metrics.

**Query Parameters:**
- `cluster_type` (optional): "GENERAL" or "STORAGE"
- `min_score` (default: 50): Minimum recommendation score (0-100)

**Response:**
```json
[
  {
    "recommendation_id": "rec_abc123",
    "action": "migrate_user",
    "user_id": "user_xyz",
    "source_vm": "general-vm-1",
    "target_vm": "general-vm-2",
    "score": 85,
    "reasons": [
      "Severe CPU imbalance: Source VM at 85.3%, Target at 22.1%",
      "Source VM overloaded at 85.3% CPU",
      "Target VM has available capacity (1/5 users, 22.1% CPU)"
    ],
    "expected_improvements": {
      "cpu_reduction_source": "42.6%",
      "performance_gain": "30-50% faster response times expected"
    },
    "estimated_downtime_seconds": 20,
    "cost_impact_usd": 0.0,
    "confidence": 95,
    "generated_at": "2025-06-15T14:30:00Z",
    "status": "PENDING"
  }
]
```

**Scoring Algorithm (6 Factors):**
1. **CPU Load Imbalance** (35 points): Source > 30% higher than target
2. **Source Overload** (25 points): Source CPU > 70%
3. **Target Capacity** (15 points): Target < 50% CPU and < 5 users
4. **Cost Savings** (15 points): Can stop source VM (consolidation)
5. **Session Duration** (10 points): Shorter = less disruption
6. **User Priority Adjustment** (varies): Low priority = lower score

**Recommendation Types:**
- `migrate_user`: Move single user to balance load
- `consolidate`: Move all users from underutilized VM
- `preemptive_scale`: Start additional VM proactively (80%+ capacity)

---

### 7. Apply Recommendation
**POST** `/admin/apply-recommendation/{recommendation_id}`

Execute a specific migration recommendation.

**Response:**
```json
{
  "success": true,
  "message": "Recommendation rec_abc123 applied"
}
```

---

### 8. Get Cluster Health
**GET** `/admin/cluster-metrics/{cluster_type}`

Aggregated health metrics for entire cluster.

**Example:** `GET /admin/cluster-metrics/GENERAL`

**Response:**
```json
{
  "cluster_type": "GENERAL",
  "total_vms": 2,
  "running_vms": 2,
  "total_active_users": 5,
  "average_cpu_usage": 48.7,
  "vms": [
    {
      "vm_name": "general-vm-1",
      "status": "RUNNING",
      "active_users": 3,
      "cpu_usage": 62.3,
      "memory_usage": 71.2,
      "last_updated": "2025-06-15T14:20:00Z"
    },
    {
      "vm_name": "general-vm-2",
      "status": "RUNNING",
      "active_users": 2,
      "cpu_usage": 35.1,
      "memory_usage": 48.6,
      "last_updated": "2025-06-15T14:20:00Z"
    }
  ]
}
```

**Dashboard Use Case:**
- Real-time monitoring frontend
- 3D visualization of VM load distribution
- Alert triggers (CPU > 80%, users > 20)

---

### 9. Predict Cluster Load
**GET** `/admin/predict-load?cluster_type=GENERAL`

Predict cluster state in 1 hour based on trends.

**Response:**
```json
{
  "predicted_in_1_hour": {
    "average_cpu": 52.3,
    "total_users": 6
  },
  "current": {
    "average_cpu": 48.7,
    "total_users": 5
  },
  "trend": "increasing",
  "recommendation": "Consider starting additional VM preemptively"
}
```

**Prediction Algorithm:**
- Simple linear extrapolation (placeholder for ML model)
- Trends: "increasing", "decreasing", "stable"
- Future enhancement: LSTM/ARIMA models trained on historical data

---

## Legacy Endpoints (Basic VM Operations)

### 10. List All VMs
**GET** `/list`

```json
{
  "vms": [
    {
      "name": "general-vm-1",
      "status": "RUNNING",
      "machine_type": "e2-micro",
      "zone": "us-central1-a",
      "external_ip": "34.123.45.67"
    }
  ]
}
```

### 11. Start VM
**POST** `/{vm_name}/start`

```json
{
  "name": "general-vm-1",
  "status": "STARTING",
  "details": { ... }
}
```

### 12. Stop VM
**POST** `/{vm_name}/stop`

### 13. Get VM Details
**GET** `/{vm_name}/details`

---

## Background Tasks (Celery Beat)

**Automated Processes:**
1. **Metrics Collection** (every 5 min): Collect CPU/RAM/disk/network from GCP Monitoring API
2. **Auto-Release** (every 10 min): Release inactive assignments (>30 min), stop empty VMs
3. **Health Check** (every 15 min): Generate alerts for overload/underload conditions
4. **Metrics Cleanup** (daily 12:30 AM): Delete metrics older than 7 days

**Start Celery Workers:**
```bash
# Terminal 1: Celery worker
celery -A app.celery_worker worker --loglevel=info

# Terminal 2: Celery beat scheduler
celery -A app.celery_worker beat --loglevel=info
```

---

## Load Balancing Strategy

**Least-Connections Algorithm:**
1. Count active assignments per VM in cluster
2. Sort VMs by active_users (ascending)
3. Assign new user to VM with fewest users
4. Start VM if all are stopped

**Example:**
- User requests general cluster VM
- general-vm-1 has 3 users, general-vm-2 has 1 user
- System assigns to general-vm-2 (least connections)

---

## Cost Optimization Features

**Free Tier Optimization:**
- Shared VMs (multiple users per VM, not 1:1)
- Auto-stop VMs when no users remain
- Auto-release inactive users after 30 minutes
- 4 e2-micro VMs cost ~$1.60/month when stopped

**Example Cost Flow:**
- User requests VM → Start general-vm-1 ($0.007/hour)
- 2nd user requests → Assigned to same VM (no additional cost)
- Both users inactive 30+ min → Auto-released
- VM auto-stops → Cost drops to $0.002/hour (stopped)

---

## Error Handling

**Common Error Codes:**
- `400 Bad Request`: Invalid cluster type or missing parameters
- `404 Not Found`: No active assignment found
- `409 Conflict`: Cluster at max capacity
- `500 Internal Server Error`: GCP API failure or database error

**Example Error Response:**
```json
{
  "detail": "No active VM assignment found"
}
```

---

## Testing Guide

**1. Request VM Assignment:**
```bash
curl -X POST http://localhost:8000/api/vm/request \
  -H "Content-Type: application/json" \
  -d '{
    "workload_description": "Running a web app with Node.js",
    "priority_level": 1
  }'
```

**2. Check Assignment:**
```bash
curl http://localhost:8000/api/vm/my-assignment
```

**3. Get Recommendations:**
```bash
curl http://localhost:8000/api/vm/admin/recommendations?min_score=60
```

**4. View Cluster Health:**
```bash
curl http://localhost:8000/api/vm/admin/cluster-metrics/GENERAL
```

---

## Database Schema (MongoDB)

**Collection: `vm_assignments`**
```javascript
{
  assignment_id: "assign_abc123",
  user_id: "user_xyz",
  vm_name: "general-vm-1",
  vm_ip: "34.123.45.67",
  cluster_type: "GENERAL",
  workload_description: "Web app",
  priority_level: 1,
  assigned_at: ISODate("2025-06-15T10:30:00Z"),
  last_active: ISODate("2025-06-15T14:22:00Z"),
  status: "ACTIVE",  // ACTIVE, RELEASED, EXPIRED
  recommendation_confidence: 85
}
```

**Collection: `vm_metrics`**
```javascript
{
  vm_name: "general-vm-1",
  cpu_usage: 45.3,
  memory_usage: 62.1,
  disk_io_mb: 124.5,
  network_io_mb: 87.3,
  active_users: 2,
  uptime_hours: 18.5,
  estimated_cost_usd: 0.1295,
  status: "RUNNING",
  collected_at: ISODate("2025-06-15T14:25:00Z")
}
```

---

## Frontend Integration Examples

**React Component:**
```javascript
// Request VM
const requestVM = async (workload) => {
  const response = await fetch('/api/vm/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workload_description: workload })
  });
  return response.json();
};

// Get Recommendations
const getRecommendations = async () => {
  const response = await fetch('/api/vm/admin/recommendations?min_score=50');
  return response.json();
};
```

**3D Visualization (Three.js):**
- Display 4 VM nodes as 3D cubes
- Color-code by CPU: Green (<50%), Yellow (50-70%), Red (>70%)
- Lines connecting users to VMs
- Real-time updates via WebSocket or polling

---

## Future Enhancements

1. **ML-Based Predictions:** Replace rule-based scoring with LSTM model
2. **WebSocket Streaming:** Real-time metrics updates to dashboard
3. **Auto-Scaling:** Dynamically change VM machine types (e2-micro → e2-small)
4. **Multi-Cloud:** Support AWS EC2 and Azure VMs
5. **Session Persistence:** Redis-backed session management for migrations
6. **Advanced Monitoring:** Integration with Prometheus/Grafana
7. **Cost Forecasting:** Predict monthly costs based on usage patterns

---

## Support
For issues or questions, check logs at:
- Backend: `backend/logs/app.log`
- Celery: Console output from worker/beat processes
- GCP: Check VM console logs in GCP Console → Compute Engine
