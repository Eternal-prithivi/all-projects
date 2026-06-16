"""HttpOnly cookie helpers for JWT access + refresh tokens."""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.responses import Response as StarletteResponse

from app.utils.config import settings

ACCESS_COOKIE_NAME = "zenith_access"
REFRESH_COOKIE_NAME = "zenith_refresh"
COOKIE_PATH = "/api"


def _secure_cookies() -> bool:
    env = (getattr(settings, "ENVIRONMENT", "") or "").lower()
    if env in ("production", "staging"):
        return True
    return os.getenv("AUTH_COOKIE_SECURE", "").lower() in ("1", "true", "yes")


def _cookie_domain() -> Optional[str]:
    explicit = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
    if explicit:
        return explicit if explicit != '""' else None
    backend = (getattr(settings, "BACKEND_URL", "") or os.getenv("BACKEND_URL", "") or "").lower()
    if "rajverse.me" in backend and "onrender.com" not in backend:
        return ".rajverse.me"
    return None


def _hosts_cross_origin() -> bool:
    """True when browser cannot share httpOnly cookies between frontend and API hosts."""
    frontend = (getattr(settings, "FRONTEND_URL", "") or os.getenv("FRONTEND_URL", "") or "").strip()
    backend = (getattr(settings, "BACKEND_URL", "") or os.getenv("BACKEND_URL", "") or "").strip()
    if not frontend or not backend:
        return False
    try:
        fh = (urlparse(frontend).hostname or "").lower()
        bh = (urlparse(backend).hostname or "").lower()
        if not fh or not bh or fh == bh:
            return False
        if fh.endswith("rajverse.me") and bh.endswith("rajverse.me"):
            return False
        return True
    except Exception:
        return False


def legacy_token_body_enabled() -> bool:
    """
    Return JWT pair in login/refresh JSON (Bearer auth).

    Required for cross-origin deploys (e.g. rajverse.me → onrender.com) until
    api.rajverse.me cookie domain is live.
    """
    raw = os.getenv("AUTH_LEGACY_TOKEN_BODY", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    env = (getattr(settings, "ENVIRONMENT", "") or "").lower()
    if env in ("development", "test"):
        return True
    if env in ("production", "staging") and _hosts_cross_origin():
        return True
    return False


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    domain = _cookie_domain()
    common = {
        "httponly": True,
        "secure": _secure_cookies(),
        "samesite": "lax",
        "path": COOKIE_PATH,
    }
    if domain:
        common["domain"] = domain

    max_age_access = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    max_age_refresh = 14 * 24 * 60 * 60

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=max_age_access,
        **common,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age_refresh,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    domain = _cookie_domain()
    kwargs = {
        "path": COOKIE_PATH,
        "httponly": True,
        "secure": _secure_cookies(),
        "samesite": "lax",
    }
    if domain:
        kwargs["domain"] = domain
    response.delete_cookie(ACCESS_COOKIE_NAME, **kwargs)
    response.delete_cookie(REFRESH_COOKIE_NAME, **kwargs)


def get_access_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get(ACCESS_COOKIE_NAME)


def get_refresh_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get(REFRESH_COOKIE_NAME)


def attach_auth_cookies(response: StarletteResponse, access_token: str, refresh_token: str) -> StarletteResponse:
    set_auth_cookies(response, access_token, refresh_token)
    return response
