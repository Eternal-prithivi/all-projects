# Cloud Resource Optimization Platform - AI Agent Instructions

## Architecture Overview

**Multi-cloud SaaS platform** for managing cloud resources (VMs, storage) across AWS, GCP, and Azure with cost optimization and ML-powered recommendations.

### Tech Stack
- **Backend**: FastAPI + MongoDB + Celery + Redis
- **Frontend**: React 19 + Vite + React Router
- **Cloud SDKs**: boto3 (AWS), google-cloud-compute (GCP), azure-storage-blob (Azure)
- **Auth**: JWT with PyOTP for 2FA

### Key Components

```
backend/app/
├── auth/          # JWT authentication, 2FA routes
├── vm/            # GCP VM cluster management (core feature)
├── storage/       # Multi-cloud file upload/optimization
├── cost/          # Cost analysis endpoints
├── security/      # Secure file upload with encryption
├── dashboard/     # Analytics and metrics
└── database/      # MongoDB client singleton
```

## Critical Patterns

### 1. **Caching Strategy** (Performance Optimization)
VM operations use tiered caching to reduce expensive GCP API calls:
```python
# backend/app/vm/routes_vm.py
metrics_cache = {}           # TTL: 10 min
cluster_health_cache = {}    # TTL: 5 min
recommendations_cache = {}   # TTL: 10 min
```
**Rule**: Invalidate caches after mutations (request/release/migrate VM) using `invalidate_cluster_health_cache()`.

### 2. **MongoDB Collections**
```python
# Key collections
vm_assignments    # User ↔ VM mappings
vm_metrics        # Historical VM performance data
users             # User accounts with 2FA secrets
files             # Multi-cloud storage metadata
secure_files      # Encrypted file references (Azure)
```

### 3. **VM Assignment Flow**
```
Request VM → create_vm() → assign_vm_to_user() → MongoDB vm_assignments
Release VM → release_vm_assignment() → stop_vm() → Clear cache
Migrate → migrate_user() → Transfer data + reassign
```

### 4. **Multi-Cloud Storage Pattern**
Files route through `storage/uploader.py` → provider-specific functions:
- `upload_to_aws()` - S3 with Glacier tiering
- `upload_to_gcp()` - Cloud Storage with lifecycle rules
- `upload_to_azure()` - Blob storage with hot/cool tiers

**Recommendation Engine**: `storage/optimizer.py` suggests provider based on:
- File size, access frequency, user priority (cost/performance/balanced)

### 5. **Frontend Data Flow**
```jsx
// React Router structure
HomePage → LoginPage/RegisterPage
  ↓ (authenticated)
DashboardLayout (sidebar + header wrapper)
  ├─ DashboardPage (overview)
  ├─ StoragePage (multi-cloud upload)
  ├─ VMClusterPage (topology + multi-VM grid)
  └─ SecurityPage (encrypted files + 2FA)
```

**API Client**: `frontend/src/api.js` exports axios instance with token injection.

### 6. **VM Cluster Topology**
`frontend/src/pages/VMClusterPage.jsx` renders:
- Real-time VM status (batch-fetched via `instance_client.list()`)
- Connection wires with CSS pseudo-elements (80px height, 10px dots)
- Grid layout for multi-VM assignments (`auto-fit minmax(500px, 1fr)`)

## Development Workflows

### Running the Stack
```bash
# Backend (port 8000)
cd backend
cp .env.example .env  # Fill in cloud credentials
uvicorn app.main:app --reload

# Frontend (port 5173)
cd frontend
npm install
npm run dev

# Celery (background tasks)
cd backend
celery -A app.celery_worker worker --loglevel=info
```

### Environment Variables Required
See `backend/.env.example` for all variables. **Critical**:
- `MONGODB_URL` - Local or Atlas
- `GCP_PROJECT_ID`, `GCP_ZONE` - For VM operations
- `JWT_SECRET` - Token signing
- AWS/Azure keys - For storage features

### Testing VM Features
1. Start backend + ensure GCP credentials configured
2. Login → Navigate to "VM Cluster" page
3. Request VM → Topology updates in real-time
4. Check `vm_assignments` collection in MongoDB

## Project-Specific Conventions

### Error Handling
FastAPI routes use `HTTPException` with status codes:
```python
raise HTTPException(status_code=404, detail="VM not found")
```
Frontend shows errors via `react-toastify`.

### Data Serialization
MongoDB documents → Pydantic models:
```python
# backend/app/vm/models.py
class VMMetricsDB(BaseModel):
    vm_name: str
    cpu_utilization: float
    # ... stored in vm_metrics collection
```
Convert to dict before JSON response: `vm_metrics.model_dump()`

### CSS Architecture
Modular stylesheets per feature:
- `frontend/src/styles/vmcluster.css` - Dark theme, topology viz
- `frontend/src/styles/dashboard.css` - Card layouts
- Naming: `.vm-card`, `.connection-wire`, `.assignments-grid`

### Migration Safety
Currently on `development` branch. Safe workflow:
```bash
git status                    # Check changes
git add -A && git commit -m "Feature X"
git push origin development   # Backup to GitHub

# When stable:
git checkout fresh-start
git merge development
git push origin fresh-start
```

## Integration Points

### GCP Compute Engine
- **Instance client**: `compute_v1.InstancesClient()` in `vm/manager.py`
- **Batch operations**: Use `instance_client.list()` to avoid 1-VM-per-call overhead
- **Monitoring**: `google-cloud-monitoring` for CPU/memory metrics

### MongoDB Connection
Singleton pattern: `database/mongo_client.py` exports `mongodb_client.client`
```python
from app.database.mongo_client import get_database
DB = get_database()
collection = DB["vm_assignments"]
```

### Celery Tasks
Defined in `storage/tasks.py` for async operations:
- Storage lifecycle transitions (hot → cool → archive)
- Background optimization recommendations

## Common Pitfalls

1. **VM status shows "UNKNOWN"**: Batch-fetch all VMs at once, don't query individually
2. **Metrics endpoint 500 error**: Convert Pydantic `VMMetricsDB` to dict before returning JSON
3. **Cache stale data**: Call `invalidate_cluster_health_cache()` after VM operations
4. **Frontend CORS errors**: Backend allows `*` origins in development
5. **GCP auth fails**: Check `GCP_SERVICE_ACCOUNT_JSON_PATH` in `.env` and file exists

## Key Files to Reference

- **VM Core Logic**: `backend/app/vm/manager.py` (300+ lines)
- **Storage Optimization**: `backend/app/storage/optimizer.py`
- **Frontend Router**: `frontend/src/main.jsx` (route definitions)
- **API Entry Point**: `backend/app/main.py` (all route inclusions)
- **VM Topology UI**: `frontend/src/pages/VMClusterPage.jsx` (953 lines)

## Current State (November 2025)

- ✅ Multi-VM cluster management with real-time topology
- ✅ Performance caching (5-10 min TTL) to reduce GCP API costs
- ✅ Multi-cloud storage with ML recommendations
- ✅ 2FA security with PyOTP
- ✅ Grid layout for multiple VM assignments per user
- 🚧 On `development` branch - safe to experiment, `fresh-start` is backup

---

**When modifying this codebase**: Always test VM operations with actual GCP project, commit frequently to `development` branch, and invalidate caches after state changes.
