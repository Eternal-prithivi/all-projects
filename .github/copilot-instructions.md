# Cloud Resource Optimization Platform - AI Agent Instructions

## Architecture Overview

**Multi-cloud SaaS platform** for managing cloud resources (VMs, storage) across AWS, GCP, and Azure with cost optimization and ML-powered recommendations.

### Tech Stack
- **Backend**: FastAPI + MongoDB + Celery + Redis
- **Frontend**: React 19 + Vite + React Router
- **Cloud SDKs**: boto3 (AWS), google-cloud-compute (GCP), azure-storage-blob (Azure)
- **Auth**: JWT with PyOTP for 2FA, Session Management, Activity Logging

### Key Components

```
backend/app/
├── auth/          # JWT authentication, 2FA routes, session tracking
├── users/         # Profile management, settings, sessions, activity logs
├── vm/            # GCP VM cluster management (core feature)
├── storage/       # Multi-cloud file upload/optimization
├── cost/          # Cost analysis endpoints
├── security/      # Secure file upload with encryption, 2FA management
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
users             # User accounts with 2FA secrets, settings
files             # Multi-cloud storage metadata
secure_files      # Encrypted file references (Azure)
sessions          # Active user sessions with device/location/IP
activity_log      # User activity tracking (login, password, 2FA, etc.)
api_keys          # User-generated API keys for programmatic access
```

### 3. **Authentication & Session Management**
```python
# Login flow with session tracking
POST /api/auth/token
  → Validates credentials
  → Creates JWT token
  → Creates session entry in MongoDB (uuid, device, location, IP, timestamp)
  → Logs "Successful Login" activity
  → Returns token

# Session management
GET /api/profile/sessions
  → Lists all active sessions for user
  → Marks current session
  → Returns device, location, IP, last_active

DELETE /api/profile/sessions/{session_id}
  → Terminates specific session
  → Prevents self-termination
  → Logs activity

# Activity logging
GET /api/profile/activity?limit=10
  → Returns recent user activities
  → Actions: login, password change, 2FA enable/disable, session terminate, profile update
  → Includes timestamp, description, IP address
```

### 4. **User Settings Management**
```python
# Settings structure
GET /api/settings/
  → Returns notifications, preferences, billing settings

PUT /api/settings/notifications
  → email_notifications, budget_alerts, security_alerts, weekly_reports, maintenance_updates

PUT /api/settings/preferences
  → theme (dark/light), language, timezone, date_format, currency

PUT /api/settings/billing
  → auto_renew, payment_method

# API Keys management
GET /api/settings/api-keys
  → Lists user's API keys (masked)

POST /api/settings/api-keys
  → Generates new API key (sk-prod-{token})
  → Shows full key only once

DELETE /api/settings/api-keys/{key_id}
  → Revokes API key
```
```
Request VM → create_vm() → assign_vm_to_user() → MongoDB vm_assignments
Release VM → release_vm_assignment() → stop_vm() → Clear cache
Migrate → migrate_user() → Transfer data + reassign
### 5. **VM Assignment Flow**
```
Request VM → create_vm() → assign_vm_to_user() → MongoDB vm_assignments
Release VM → release_vm_assignment() → stop_vm() → Clear cache
Migrate → migrate_user() → Transfer data + reassign
```

### 6. **Multi-Cloud Storage Pattern**
Files route through `storage/uploader.py` → provider-specific functions:
- `upload_to_aws()` - S3 with Glacier tiering
- `upload_to_gcp()` - Cloud Storage with lifecycle rules
- `upload_to_azure()` - Blob storage with hot/cool tiers

**Recommendation Engine**: `storage/optimizer.py` suggests provider based on:
- File size, access frequency, user priority (cost/performance/balanced)

### 7. **Frontend Data Flow**
```jsx
// React Router structure
HomePage (split-screen auth) → Dashboard (authenticated)
  ↓
DashboardLayout (sidebar + header wrapper)
  ├─ DashboardPage (overview with metrics)
  ├─ StoragePage (multi-cloud upload)
  ├─ VMClusterPage (topology + multi-VM grid)
  ├─ SecurityPage (encrypted files + 2FA)
  ├─ ProfilePage (user profile management)
  ├─ SettingsPage (notifications, preferences, billing, API keys)
  └─ SecuritySettingsPage (password, 2FA, sessions, activity log)
```

**API Client**: `frontend/src/api.js` exports axios instance with token injection.

### 8. **VM Cluster Topology**
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

### Backend
- **VM Core Logic**: `backend/app/vm/manager.py` (300+ lines)
- **Storage Optimization**: `backend/app/storage/optimizer.py`
- **Authentication**: `backend/app/auth/routes_auth.py`
- **Profile Management**: `backend/app/users/routes_profile.py`
- **Settings Management**: `backend/app/users/routes_settings.py`
- **2FA Security**: `backend/app/security/routes_2fa.py`
- **API Entry Point**: `backend/app/main.py` (all route inclusions)

### Frontend
- **Router Configuration**: `frontend/src/main.jsx` (route definitions)
- **VM Topology UI**: `frontend/src/pages/VMClusterPage.jsx` (953 lines)
- **Landing Page**: `frontend/src/pages/HomePage.jsx` (split-screen auth)
- **Security Settings**: `frontend/src/pages/SecuritySettingsPage.jsx`
- **User Settings**: `frontend/src/pages/SettingsPage.jsx`
- **Profile Page**: `frontend/src/pages/ProfilePage.jsx`
- **Dashboard Layout**: `frontend/src/components/dashboard/DashboardLayout.jsx`

### Styles
- **Dashboard**: `frontend/src/styles/dashboard.css`
- **VM Cluster**: `frontend/src/styles/vmcluster.css`
- **Landing Page**: `frontend/src/styles/home.css`
- **Security Settings**: `frontend/src/styles/security-settings.css`
- **Settings Page**: `frontend/src/styles/settings.css`

## Current State (November 2025)

### Completed Features ✅
- **Authentication & Security**
  - JWT-based authentication with token refresh
  - PyOTP 2FA with QR code generation and verification
  - Session management with device/location/IP tracking
  - Activity logging for all security events
  - Password change with validation
  
- **User Management**
  - Profile page with personal info editing
  - Settings page with notifications, preferences, billing
  - API key generation and management
  - Active session viewing and termination
  - Security settings centralized page
  
- **VM Cluster Management**
  - Multi-VM cluster management with real-time topology
  - Performance caching (5-10 min TTL) to reduce GCP API costs
  - Grid layout for multiple VM assignments per user
  - SSH key generation and management
  - VM metrics and cluster health monitoring
  
- **Storage Management**
  - Multi-cloud storage with ML recommendations
  - Intelligent tiering (hot/cool/archive)
  - Cost estimation per provider
  
- **User Interface**
  - Split-screen authentication landing page
    * Purple gradient branding with feature highlights
    * Dark theme auth card with login/signup tabs
    * Modern SaaS design
  - Dark theme dashboard with sidebar navigation
  - Breadcrumb navigation with working home button
  - Profile dropdown with quick access to settings
  - Toast notifications for user feedback
  - Responsive design for mobile/tablet

### Backend Architecture
- **New Routes Added**:
  - `routes_profile.py` - Session and activity management
  - `routes_settings.py` - User settings and API keys
  - Enhanced `routes_auth.py` - Session tracking on login
  - Enhanced `routes_2fa.py` - Activity logging

- **Database Schema**:
  ```python
  # users collection
  {
    "username": str,
    "email": str,
    "hashed_password": str,
    "totp_secret": str (optional),
    "settings": {
      "notifications": {...},
      "preferences": {...},
      "billing": {...}
    }
  }
  
  # sessions collection
  {
    "session_id": str (uuid),
    "username": str,
    "device": str,
    "location": str,
    "ip_address": str,
    "created_at": datetime,
    "last_active": datetime,
    "is_current": bool
  }
  
  # activity_log collection
  {
    "username": str,
    "action": str,
    "description": str,
    "ip_address": str (optional),
    "timestamp": datetime
  }
  
  # api_keys collection
  {
    "key_id": str,
    "key": str,
    "username": str,
    "created_at": datetime,
    "last_used": datetime,
    "revoked": bool
  }
  ```

### Frontend Architecture
- **New Pages**:
  - `SecuritySettingsPage.jsx` - Password, 2FA, sessions, activity
  - Updated `HomePage.jsx` - Split-screen auth landing
  - Enhanced `ProfilePage.jsx` - User profile management
  - Enhanced `SettingsPage.jsx` - Comprehensive settings UI

- **New Styles**:
  - `security-settings.css` - Security page styling
  - Updated `home.css` - Split-screen auth design
  - Updated `breadcrumbs.css` - Navigation fixes

### Branch Status
- 🚧 On `development` branch - latest features
- ✅ All changes pushed to GitHub
- 🔄 Ready to merge to `main`/`fresh-start` when stable

### Recent Updates (November 19, 2025)
1. **Session Management System**
   - Track all user sessions with device info
   - View active sessions in Security Settings
   - Terminate individual sessions (except current)
   - Auto-cleanup of old sessions

2. **Activity Logging**
   - Log all security-related actions
   - Display in Security Settings with icons
   - Include timestamps and IP addresses
   - Actions logged: login, password change, 2FA enable/disable, session terminate, profile update

3. **Split-Screen Landing Page**
   - Replaced marketing page with focused auth experience
   - Left side: Branding with gradient and features
   - Right side: Login/signup forms with tab switcher
   - Auto-redirect logged-in users to dashboard
   - Form validation and loading states

4. **Settings Management**
   - Notification preferences (email, budgets, security)
   - User preferences (theme, language, timezone)
   - Billing settings (auto-renew, payment method)
   - API key generation with secure storage

5. **Navigation Improvements**
   - Fixed breadcrumb home button with proper navigation
   - Added Security link to profile dropdown
   - Unified settings access across the app

---

**When modifying this codebase**: Always test VM operations with actual GCP project, commit frequently to `development` branch, and invalidate caches after state changes.
