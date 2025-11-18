from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import routes_auth
from app.dashboard import routes_dashboard
from app.users import routes_users
from app.users import routes_profile
from app.users import routes_settings
from app.storage import routes_storage
from app.security import routes_security
from app.websockets import routes_ws
from app.security import routes_2fa
from app.cost import routes_cost
from app.cost import routes_export
from app.cost import routes_forecast
from app.cost import routes_anomaly
from app.vm import routes_vm
from app.vm import routes_admin_cleanup  # Temporary admin cleanup endpoint
from app.pricing import routes_pricing
from app.budgets import routes_budgets
from app.database.mongo_client import mongodb_client
from app.utils.config import settings
import os

app = FastAPI(title="Zenith API")

# Correct CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include all API routers with the /api prefix

app.include_router(routes_auth.router, prefix="/api/auth")
app.include_router(routes_users.router, prefix="/api/users")
app.include_router(routes_profile.router, prefix="/api")
app.include_router(routes_settings.router, prefix="/api")
app.include_router(routes_dashboard.router, prefix="/api/dashboard")
app.include_router(routes_storage.router, prefix="/api/storage")
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
