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
from app.notifications import routes_notifications
from app.organizations import routes_organizations
from app.auth import routes_sso
from app.database.mongo_client import mongodb_client
from app.utils.config import settings
import os
import re

from app.utils.gcp_credentials import gcp_credentials_file_present


def _init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=getattr(settings, "ENVIRONMENT", "development"),
            integrations=[FastApiIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            send_default_pii=False,
        )
    except Exception as exc:
        print(f"⚠️  Sentry init skipped: {exc}")


_init_sentry()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Zenith API")

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — explicit allowlist + Vercel patterns (see docs/setup/DEPLOYMENT_SECRETS.md)
_STATIC_ALLOWED_ORIGINS = [
    "https://rajverse.me",
    "https://www.rajverse.me",
]

_VERCEL_FRONTEND_PATTERNS = [
    r"https://zenith-frontend-.*\.vercel\.app$",
    r"https://zenith-frontend-.*-eternal-prithivis-projects\.vercel\.app$",
]

# Development only — broader preview URLs
_VERCEL_DEV_EXTRA_PATTERNS = [
    r"https://zenith-.*-eternal-prithivis-projects\.vercel\.app$",
]


def _extra_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


def is_allowed_origin(origin: str) -> bool:
    """Return True if the browser Origin may call this API with credentials."""
    if not origin:
        return False

    normalized = origin.rstrip("/")
    env = getattr(settings, "ENVIRONMENT", "development") or "development"

    for extra in _extra_cors_origins():
        if normalized == extra.rstrip("/"):
            return True

    frontend_url = (os.getenv("FRONTEND_URL") or getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    if frontend_url and normalized == frontend_url:
        return True

    if normalized in _STATIC_ALLOWED_ORIGINS:
        return True

    if env != "production":
        if normalized.startswith("http://localhost:") or normalized.startswith("http://127.0.0.1:"):
            return True

    patterns = list(_VERCEL_FRONTEND_PATTERNS)
    if env != "production":
        patterns.extend(_VERCEL_DEV_EXTRA_PATTERNS)

    for pattern in patterns:
        if re.match(pattern, origin):
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
app.include_router(routes_sso.router, prefix="/api/auth")
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
app.include_router(routes_notifications.router, prefix="/api")
app.include_router(routes_organizations.router, prefix="/api")

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Zenith API!"}


@app.get("/health", tags=["Health"])
def health_check():
    """
    Liveness probe for Render — must respond in <5s without waiting on MongoDB/Terraform.
    """
    return {"status": "ok", "service": "zenith-api"}


@app.get("/health/ready", tags=["Health"])
def health_ready():
    """Readiness probe — includes dependency status (may be slower)."""
    mongo_ok = mongodb_client.is_connected() or mongodb_client.connect()
    return {
        "status": "ok" if mongo_ok else "degraded",
        "mongo_connected": mongo_ok,
        "gcp_credentials_present": gcp_credentials_file_present(),
        "environment": getattr(settings, "ENVIRONMENT", "development"),
    }


@app.on_event("startup")
def on_startup():
    """Connect MongoDB and log Terraform status without blocking the HTTP server."""
    import threading

    if getattr(settings, "ENVIRONMENT", "") == "test":
        from app.utils.rate_limit import disable_rate_limits

        disable_rate_limits(app)

    def _warm_dependencies() -> None:
        mongodb_client.connect()
        try:
            from app.provision.routes_provision import recover_plans_interrupted_by_restart

            n = recover_plans_interrupted_by_restart()
            if n:
                print(f"⚠️  Marked {n} interrupted terraform plan(s) as failed after restart.")
        except Exception as exc:
            print(f"⚠️  Plan recovery skipped: {exc}")

        from app.provision.terraform_runner import (
            check_terraform_installed,
            get_terraform_version,
        )

        if check_terraform_installed():
            version = get_terraform_version()
            print(f"\u2705 Terraform CLI detected: v{version}")
        else:
            print("\u26a0\ufe0f  Terraform CLI not found — /api/provision endpoints will return 503")

    threading.Thread(target=_warm_dependencies, daemon=True).start()
