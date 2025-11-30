# Cloud Resource Optimization Platform (Zenith)

> **Intelligent multi-cloud resource management platform** that reduces cloud costs by up to 60% while improving performance across AWS, GCP, and Azure.

![Platform](https://img.shields.io/badge/Platform-Multi--Cloud-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Frontend](https://img.shields.io/badge/Frontend-React%2019-blue)
![Database](https://img.shields.io/badge/Database-MongoDB-green)
![License](https://img.shields.io/badge/License-Proprietary-red)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

### 🔐 Authentication & Security
- **JWT Authentication** with secure token management
- **Two-Factor Authentication (2FA)** using PyOTP with QR code generation
- **Session Management** - Track active sessions with device, location, and IP
- **Activity Logging** - Comprehensive audit trail of all security events
- **API Key Management** - Generate and manage programmatic access keys
- **Password Management** - Secure password change with validation

### 👤 User Management
- **Profile Management** - Edit personal information and settings
- **Notification Preferences** - Control email, budget, and security alerts
- **User Preferences** - Customize theme, language, timezone, date format, currency
- **Billing Settings** - Manage auto-renewal and payment methods
- **Active Sessions** - View and terminate sessions from any device
- **Activity History** - Review recent account activities with timestamps

### 🖥️ VM Cluster Management
- **Multi-VM Assignment** - Request and manage multiple VMs per user
- **Real-Time Topology** - Visual representation of VM clusters with status
- **Performance Monitoring** - Track CPU, memory, and network metrics
- **SSH Key Management** - Generate and download SSH keys for secure access
- **VM Operations** - Start, stop, release, and migrate VMs
- **Cluster Health** - Monitor overall cluster status and recommendations
- **Smart Caching** - 5-10 minute TTL to reduce expensive GCP API calls

### 💾 Multi-Cloud Storage
- **Provider Selection** - Upload to AWS S3, GCP Cloud Storage, or Azure Blob
- **ML-Powered Recommendations** - Intelligent provider suggestions based on usage
- **Cost Estimation** - Compare costs across providers before upload
- **Intelligent Tiering** - Automatic lifecycle management (hot → cool → archive)
- **Secure File Upload** - Encryption and sensitive data detection
- **File Management** - List, download, and manage uploaded files

### 📊 Cost Analysis & Optimization
- **Real-Time Analytics** - Monitor cloud spending across all providers
- **Cost Forecasting** - ML-powered predictions for future costs
- **Budget Alerts** - Notifications when approaching spending limits
- **Optimization Recommendations** - AI suggestions to reduce costs
- **Provider Comparison** - Side-by-side cost analysis
- **Historical Trends** - Track spending patterns over time

### 🎨 Modern User Interface
- **Split-Screen Landing Page** - Professional authentication experience
  - Purple gradient branding with feature highlights
  - Tab-based login/signup forms
  - Auto-redirect for authenticated users
- **Dark Theme Dashboard** - Modern, easy-on-the-eyes interface
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Sidebar Navigation** - Quick access to all features
- **Breadcrumb Navigation** - Always know where you are
- **Toast Notifications** - Real-time feedback for all actions
- **Profile Dropdown** - Quick access to settings and logout

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐
│   Users/Devices │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  React   │
    │  Client  │
    └────┬─────┘
         │
    ┌────▼──────┐
    │  FastAPI  │
    │  Backend  │
    └─┬──┬──┬──┘
      │  │  │
   ┌──▼──▼──▼─────────────┐
   │  MongoDB  │  Redis   │
   └───────────┴──────────┘
      │  │  │
   ┌──▼──▼──▼─────────────┐
   │  AWS  │ GCP │ Azure  │
   └────────────────────────┘
```

### Backend Architecture

```
backend/app/
├── auth/              # Authentication & JWT
│   ├── routes_auth.py     # Login, register, token endpoints
│   ├── auth_service.py    # Authentication logic
│   └── auth_utils.py      # Helper functions
├── users/             # User management
│   ├── routes_profile.py  # Profile, sessions, activity
│   ├── routes_settings.py # Settings, API keys
│   └── user_model.py      # User Pydantic models
├── vm/                # Virtual Machine management
│   ├── routes_vm.py       # VM operations endpoints
│   ├── manager.py         # GCP VM management logic
│   └── models.py          # VM data models
├── storage/           # Multi-cloud storage
│   ├── routes_storage.py  # File upload endpoints
│   ├── uploader.py        # Multi-cloud upload logic
│   ├── optimizer.py       # ML recommendation engine
│   └── tasks.py           # Celery background tasks
├── cost/              # Cost analysis
│   ├── routes_cost.py     # Cost endpoints
│   └── manager.py         # Cost calculation logic
├── security/          # Security features
│   ├── routes_2fa.py      # 2FA setup and verification
│   └── routes_security.py # Secure file operations
├── dashboard/         # Dashboard analytics
│   └── routes_dashboard.py
└── database/          # Database connections
    └── mongo_client.py    # MongoDB singleton
```

### Frontend Architecture

```
frontend/src/
├── pages/                  # Main application pages
│   ├── HomePage.jsx            # Split-screen auth landing
│   ├── DashboardPage.jsx       # Main dashboard
│   ├── VMClusterPage.jsx       # VM management
│   ├── StoragePage.jsx         # File storage
│   ├── ProfilePage.jsx         # User profile
│   ├── SettingsPage.jsx        # User settings
│   └── SecuritySettingsPage.jsx # Security management
├── components/            # Reusable components
│   ├── dashboard/
│   │   ├── DashboardLayout.jsx # Main layout wrapper
│   │   ├── Header.jsx          # Top navigation
│   │   └── Sidebar.jsx         # Side navigation
│   ├── Breadcrumbs.jsx        # Navigation breadcrumbs
│   ├── ProfileDropdown.jsx    # User menu
│   └── EmptyState.jsx         # Empty states
├── context/              # React Context
│   └── AuthContext.jsx       # Authentication state
├── styles/               # CSS modules
│   ├── home.css              # Landing page
│   ├── dashboard.css         # Dashboard
│   ├── vmcluster.css         # VM cluster
│   ├── security-settings.css # Security page
│   └── settings.css          # Settings page
└── api.js                # Axios API client
```

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: MongoDB 7.0+
- **Task Queue**: Celery + Redis
- **Authentication**: JWT + PyOTP (2FA)
- **Cloud SDKs**:
  - AWS: boto3
  - GCP: google-cloud-compute, google-cloud-storage
  - Azure: azure-storage-blob
- **ML/Analytics**: scikit-learn, pandas

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite 5
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Notifications**: React Toastify
- **QR Code**: qrcode.react
- **Charts**: Recharts
- **Styling**: CSS Modules

### DevOps
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: (To be implemented)
- **Logging**: Python logging + FastAPI middleware

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+
- **MongoDB** 7.0+ (local or Atlas)
- **Redis** (for Celery)
- **Cloud Accounts** (optional):
  - AWS account with S3 access
  - GCP project with Compute Engine enabled
  - Azure account with Blob Storage

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Eternal-prithivi/all-projects.git
   cd CloudResourceOptimizationPlatform
   ```

2. **Backend Setup**
   ```bash
   cd backend
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create .env file
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   
   # Install dependencies
   npm install
   ```

4. **Configure Environment Variables**
   
   Edit `backend/.env`:
   ```env
   # MongoDB
   MONGODB_URL=mongodb://localhost:27017/cloud_optimization
   
   # JWT
   JWT_SECRET=your-super-secret-key-change-this-in-production
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # GCP (for VM management)
   GCP_PROJECT_ID=your-gcp-project-id
   GCP_ZONE=us-central1-a
   GCP_SERVICE_ACCOUNT_JSON_PATH=/path/to/service-account.json
   
   # AWS (for storage)
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_REGION=us-east-1
   
   # Azure (for storage)
   AZURE_STORAGE_CONNECTION_STRING=your-azure-connection-string
   
   # Redis (for Celery)
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Start the Services**

   **Terminal 1 - Backend API**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   **Terminal 2 - Celery Worker**
   ```bash
   cd backend
   source venv/bin/activate
   celery -A app.celery_worker worker --loglevel=info
   ```

   **Terminal 3 - Celery Beat (Scheduler)**
   ```bash
   cd backend
   source venv/bin/activate
   celery -A app.celery_worker beat --loglevel=info
   ```

   **Terminal 4 - Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

6. **Access the Application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### First Time Setup

1. Visit http://localhost:5173
2. Click "Sign Up" tab on the split-screen landing page
3. Create your account with email, username, and password
4. Login with your credentials
5. Explore the dashboard!

## 📁 Project Structure

```
CloudResourceOptimizationPlatform/
├── backend/
│   ├── app/
│   │   ├── auth/           # Authentication
│   │   ├── users/          # User management
│   │   ├── vm/             # VM operations
│   │   ├── storage/        # Cloud storage
│   │   ├── cost/           # Cost analysis
│   │   ├── security/       # Security features
│   │   ├── dashboard/      # Dashboard
│   │   ├── database/       # DB connections
│   │   ├── main.py         # FastAPI app entry
│   │   └── celery_worker.py # Celery config
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment template
├── frontend/
│   ├── src/
│   │   ├── pages/          # React pages
│   │   ├── components/     # React components
│   │   ├── context/        # React context
│   │   ├── styles/         # CSS files
│   │   ├── main.jsx        # React entry point
│   │   └── api.js          # API client
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
├── docs/                   # Documentation
├── devops/                 # Docker, CI/CD
├── .github/                # GitHub config
│   └── copilot-instructions.md # AI agent guide
└── README.md              # This file
```

## 📚 API Documentation

### Authentication Endpoints

#### POST /api/auth/register
Create a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "message": "User registered successfully"
}
```

#### POST /api/auth/token
Login and receive JWT token.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### User Profile Endpoints

#### GET /api/profile/me
Get current user profile (requires authentication).

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "created_at": "2025-11-19T10:00:00Z"
}
```

#### GET /api/profile/sessions
List all active sessions.

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid-here",
      "device": "Chrome on MacOS",
      "location": "New York, US",
      "ip_address": "192.168.1.1",
      "last_active": "2025-11-19T14:30:00Z",
      "current": true
    }
  ]
}
```

#### GET /api/profile/activity?limit=10
Get recent account activities.

**Response:**
```json
{
  "activities": [
    {
      "action": "login",
      "description": "Successful Login",
      "timestamp": "2025-11-19T14:30:00Z",
      "ip_address": "192.168.1.1"
    }
  ]
}
```

### Settings Endpoints

#### GET /api/settings/
Get user settings.

**Response:**
```json
{
  "notifications": {
    "email_notifications": true,
    "budget_alerts": true,
    "security_alerts": true
  },
  "preferences": {
    "theme": "dark",
    "language": "en",
    "timezone": "UTC-5"
  },
  "billing": {
    "auto_renew": true,
    "payment_method": "Credit Card ****1234"
  }
}
```

#### GET /api/settings/api-keys
List API keys (masked).

**Response:**
```json
{
  "success": true,
  "keys": [
    {
      "key_id": "abc123",
      "key_preview": "sk-prod-****************************xyz789",
      "created_at": "2025-11-19T10:00:00Z"
    }
  ]
}
```

### VM Management Endpoints

#### GET /api/vm/assignment
Get user's VM assignments.

#### POST /api/vm/request
Request a new VM.

#### POST /api/vm/release/{vm_name}
Release a VM.

#### GET /api/vm/metrics
Get VM performance metrics.

#### GET /api/vm/cluster-health
Get cluster health status.

For complete API documentation, visit: http://localhost:8000/docs

## 🧑‍💻 Development Guide

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style

**Backend (Python)**
- Follow PEP 8
- Use type hints
- Document functions with docstrings

**Frontend (JavaScript/React)**
- Use ESLint configuration
- Follow React best practices
- Use functional components with hooks

### Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "feat: description"`
3. Push to remote: `git push origin feature/your-feature`
4. Create pull request to `development` branch

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

## 🚢 Deployment

### Docker Deployment

1. **Build images**
   ```bash
   docker-compose build
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Check logs**
   ```bash
   docker-compose logs -f
   ```

### Production Checklist

- [ ] Update `.env` with production values
- [ ] Set strong `JWT_SECRET`
- [ ] Configure production MongoDB (Atlas)
- [ ] Set up Redis in production
- [ ] Configure cloud provider credentials
- [ ] Enable HTTPS
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline

## 🤝 Contributing

This is a proprietary project. External contributions are not currently accepted.

For internal development:

### Development Branch Strategy

- `main` - Production-ready code
- `development` - Latest development code
- `feature/*` - New features
- `fix/*` - Bug fixes

## 📄 License

This software is proprietary and confidential. All rights reserved.

**Copyright (c) 2025 Cloud Resource Optimization Platform. All Rights Reserved.**

Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without explicit written permission from the copyright holder.

## 🙏 Acknowledgments

- FastAPI for the amazing Python web framework
- React team for the powerful UI library
- MongoDB for the flexible database
- All cloud providers (AWS, GCP, Azure) for their APIs

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Email: support@zenith-cloud.com
- Documentation: [docs/](docs/)

---

**Built with ❤️ by the Zenith Team**

*Last Updated: November 19, 2025*
# Auto-deploy test - 2025-11-30_19:16:46

✅ Auto-deploy verified - Sun Nov 30 19:24:15 IST 2025
🚀 Webhook test
