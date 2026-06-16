"""Enterprise SSO — Google OAuth when configured; OIDC settings from platform_config."""

import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.auth.auth_utils import create_access_token, get_password_hash
from app.database.mongo_client import get_database, get_users_collection
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/sso", tags=["SSO"])

def _platform_settings():
    doc = get_database()["platform_settings"].find_one({"_id": "platform_config"}) or {}
    return doc


def _google_configured() -> bool:
    return bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID") and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"))


@router.get("/providers")
def list_sso_providers():
    """Public list of SSO options for the login page."""
    plat = _platform_settings()
    google_enabled = plat.get("sso_google_enabled", False) and _google_configured()
    oidc_enabled = bool(plat.get("sso_oidc_enabled") and plat.get("sso_oidc_issuer"))

    providers = []
    if google_enabled:
        providers.append({"id": "google", "name": "Google", "type": "oauth2"})
    if oidc_enabled:
        providers.append(
            {
                "id": "oidc",
                "name": plat.get("sso_oidc_display_name", "Enterprise SSO"),
                "type": "oidc",
            }
        )
    return {
        "providers": providers,
        "google_configured": _google_configured(),
        "oidc_configured": oidc_enabled,
    }


@router.get("/google/login")
def google_login_start():
    if not _google_configured():
        raise HTTPException(status_code=501, detail="Google SSO is not configured on this server")
    plat = _platform_settings()
    if not plat.get("sso_google_enabled", False):
        raise HTTPException(status_code=403, detail="Google SSO is disabled by administrator")

    redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/api/auth/sso/google/callback"
    # Google callback must hit backend — use backend URL
    backend_base = os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{backend_base}/api/auth/sso/google/callback"

    params = {
        "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_login_callback(code: str):
    if not _google_configured():
        raise HTTPException(status_code=501, detail="Google SSO not configured")

    backend_base = os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{backend_base}/api/auth/sso/google/callback"

    try:
        import httpx
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="Google SSO requires httpx. Run: pip install httpx",
        ) from exc

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            logger.error("Google token exchange failed: %s", token_res.text)
            raise HTTPException(status_code=400, detail="SSO token exchange failed")

        tokens = token_res.json()
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google profile")

        profile = user_res.json()

    email = profile.get("email")
    google_id = profile.get("id")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    users = get_users_collection()
    user = users.find_one({"google_id": google_id}) or users.find_one({"email": email.lower()})

    if not user:
        from app.trust.signup_guards import assert_email_allowed

        assert_email_allowed(email.lower())

        base_username = email.split("@")[0].replace(".", "_")[:40]
        username = base_username
        suffix = 0
        while users.find_one({"username": username}):
            suffix += 1
            username = f"{base_username}{suffix}"

        users.insert_one(
            {
                "username": username,
                "email": email.lower(),
                "hashed_password": get_password_hash(secrets.token_urlsafe(24)),
                "role": "user",
                "email_verified": True,
                "google_id": google_id,
                "sso_provider": "google",
                "two_fa_enabled": False,
                "two_fa_verified": False,
            }
        )
        user = users.find_one({"username": username})
        from app.trust.signup_notify import notify_new_user_signup

        notify_new_user_signup(
            username=username,
            email=email.lower(),
            source="google_sso",
        )
    else:
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {"google_id": google_id, "email_verified": True}},
        )

    from app.trust.sso_exchange import create_sso_exchange_code

    code = create_sso_exchange_code(user["username"])
    frontend = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(f"{frontend}/auth/sso/callback?code={code}")


@router.post("/exchange")
async def sso_exchange_code(body: dict):
    """Exchange short-lived SSO code for JWT pair (sets httpOnly cookies)."""
    from app.trust.sso_exchange import consume_sso_exchange_code
    from app.auth.token_service import issue_token_pair
    from app.auth.routes_auth import _auth_token_response

    code = (body or {}).get("code", "")
    username = consume_sso_exchange_code(code)
    access, refresh = issue_token_pair(username)
    return _auth_token_response(access, refresh)


@router.get("/oidc/login")
def oidc_login_start():
    plat = _platform_settings()
    issuer = plat.get("sso_oidc_issuer")
    if not plat.get("sso_oidc_enabled") or not issuer:
        raise HTTPException(status_code=501, detail="Enterprise OIDC is not configured")
    return RedirectResponse(issuer)
