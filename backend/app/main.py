# =============================================================================
# MODULE: main.py  (180 lines)
# PURPOSE: FastAPI app entry point — all routers mounted here, CORS, middleware
# IMPORTANT ROUTER NOTES:
#   - routes_auth.py is mounted TWICE: /api/auth AND /auth (legacy alias)
#   - Admin routes have NO prefix — they mount directly (admin/dashboard, audit-logs)
#   - CORS: allow_origins=["*"] — RESTRICT before public deployment
# ENTRY POINT: uvicorn app.main:app --reload → http://localhost:8000
# API DOCS: http://localhost:8000/docs (Swagger auto-generated)
# DO NOT:
#   - Add new routers without checking for prefix conflicts
#   - Remove the /auth legacy alias until frontend is updated to /api/auth only
#   - Change CORS to restrict without testing all frontend API calls still work
# =============================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.auth import routes_auth
from app.auth import routes_password_reset
from app.dashboard import routes_dashboard
from app.users import routes_users
from app.users import routes_profile
from app.users import routes_settings
from app.storage import routes_storage
from app.contact import routes_contact
from app.security import routes_security
from app.websockets import routes_ws
from app.security import routes_2fa
from app.cost import routes_cost
from app.cost import routes_export
from app.cost import routes_forecast
from app.cost import routes_anomaly
from app.vm import routes_vm
from app.vm import routes_admin_cleanup  # Temporary admin cleanup endpoint
from app.admin import routes_admin
from app.setup import routes_setup
from app.pricing import routes_pricing
from app.budgets import routes_budgets
from app.billing import routes_billing
from app.payments import routes_payments
from app.byoc import routes_byoc
from app.ml import routes_feedback
from app.provision import routes_provision
from app.platform import routes_platform
from app.database.mongo_client import mongodb_client
from app.utils.config import settings
import os
import re

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Zenith API")

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration - Allow Vercel preview deployments with pattern matching
def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed (localhost or Vercel domains)"""
    if not origin:
        return False
    
    # Allow local dev (Vite may use localhost or 127.0.0.1)
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return True
    
    # Allow all Vercel preview and production URLs
    vercel_patterns = [
        r"https://zenith-frontend-.*\.vercel\.app$",
        r"https://zenith-frontend-.*-eternal-prithivis-projects\.vercel\.app$",
        r"https://zenith-.*-eternal-prithivis-projects\.vercel\.app$",
    ]
    
    for pattern in vercel_patterns:
        if re.match(pattern, origin):
            return True
    
    # Allow custom domains
    allowed_domains = [
        "https://rajverse.me",
        "https://www.rajverse.me"
    ]
    if origin in allowed_domains:
        return True
    
    # Allow custom domain if set via environment
    custom_domain = os.getenv("FRONTEND_URL")
    if custom_domain and origin == custom_domain:
        return True
    
    return False

# Headers allowed on cross-origin requests (login sends X-Device-Fingerprint)
_CORS_ALLOW_HEADERS = (
    "Content-Type, Authorization, Accept, Origin, User-Agent, X-Device-Fingerprint"
)

# Custom CORS middleware to handle dynamic Vercel URLs
class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight OPTIONS requests immediately
        if request.method == "OPTIONS":
            from starlette.responses import Response
            response = Response(status_code=200)
            
            # Add CORS headers if origin is allowed
            if origin and is_allowed_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = _CORS_ALLOW_HEADERS
                response.headers["Access-Control-Max-Age"] = "86400"
            
            return response
        
        # Process the actual request
        response = await call_next(request)
        
        # Add CORS headers to response if origin is allowed
        if origin and is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = _CORS_ALLOW_HEADERS
        
        return response

# Add the custom CORS middleware
app.add_middleware(DynamicCORSMiddleware)


# Include all API routers with the /api prefix

app.include_router(routes_auth.router, prefix="/api/auth")
app.include_router(routes_password_reset.router, prefix="/api/auth")
app.include_router(routes_users.router, prefix="/api/users")
app.include_router(routes_profile.router, prefix="/api")
app.include_router(routes_settings.router, prefix="/api")
app.include_router(routes_dashboard.router, prefix="/api/dashboard")
app.include_router(routes_storage.router, prefix="/api/storage")
app.include_router(routes_contact.router)
app.include_router(routes_security.router, prefix="/api/security")
app.include_router(routes_2fa.router, prefix="/api/2fa")
app.include_router(routes_ws.router, prefix="/ws")
#app.include_router(routes_cost.router, prefix="/cost", tags=["cost"])
app.include_router(routes_auth.router, prefix="/auth", tags=["Auth"])
# Cost analysis endpoints follow /api/<feature> convention for consistency
app.include_router(routes_cost.router, prefix="/api/cost", tags=["Cost"])
app.include_router(routes_export.router, prefix="/api/cost", tags=["Cost Export"])
app.include_router(routes_forecast.router, prefix="/api/cost", tags=["Cost Forecast"])
app.include_router(routes_anomaly.router, prefix="/api/cost", tags=["Cost Anomaly"])
app.include_router(routes_pricing.router, prefix="/api", tags=["Pricing"])
app.include_router(routes_budgets.router, prefix="/api/budgets", tags=["Budgets"])
app.include_router(routes_vm.router, prefix="/api/vm", tags=["Virtual Machines"])
app.include_router(routes_admin_cleanup.router, prefix="/api", tags=["Admin"])  # Cleanup endpoint
app.include_router(routes_admin.router)
app.include_router(routes_billing.router, prefix="/api", tags=["Billing"])
app.include_router(routes_payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(routes_byoc.router, prefix="/api/byoc", tags=["BYOC"])
app.include_router(routes_feedback.router, prefix="/api/ml", tags=["ML Feedback"])
app.include_router(routes_provision.router, prefix="/api/provision", tags=["Provisioning"])
app.include_router(routes_platform.router, prefix="/api/platform", tags=["Platform"])

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Zenith API!"}


@app.get("/health", tags=["Health"])
def health_check():
    """Simple health check that reports MongoDB connection and GCP credential status."""
    mongo_ok = False
    try:
        mongo_ok = mongodb_client.client is not None
    except Exception:
        mongo_ok = False

    gcp_key = getattr(settings, 'GCP_SERVICE_ACCOUNT_JSON_PATH', None)
    if not gcp_key:
        # fallback for legacy name
        gcp_key = getattr(settings, 'GCP_SA_KEY_PATH', None)

    gcp_ok = False
    if gcp_key:
        # If absolute path, check directly; if relative, resolve relative to project root
        if os.path.isabs(gcp_key):
            gcp_ok = os.path.exists(gcp_key)
        else:
            # infer repo root from this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_root = os.path.dirname(base_dir)
            gcp_path = os.path.join(project_root, 'backend', gcp_key)
            gcp_ok = os.path.exists(gcp_path)

    return {"mongo_connected": mongo_ok, "gcp_credentials_present": gcp_ok}


@app.on_event("startup")
def check_terraform_on_startup():
    """Log a warning at startup if Terraform CLI is not installed."""
    from app.provision.terraform_runner import check_terraform_installed, get_terraform_version
    if check_terraform_installed():
        version = get_terraform_version()
        print(f"\u2705 Terraform CLI detected: v{version}")
    else:
        print("\u26a0\ufe0f  Terraform CLI not found — /api/provision endpoints will return 503")
