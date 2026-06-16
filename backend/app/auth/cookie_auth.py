"""HttpOnly cookie helpers for JWT access + refresh tokens."""

from __future__ import annotations

import os
from typing import Optional

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
        return explicit
    backend = (getattr(settings, "BACKEND_URL", "") or "").lower()
    if "rajverse.me" in backend:
        return ".rajverse.me"
    return None


def legacy_token_body_enabled() -> bool:
    raw = os.getenv("AUTH_LEGACY_TOKEN_BODY", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    env = (getattr(settings, "ENVIRONMENT", "") or "").lower()
    return env in ("development", "test")


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
