"""Unit tests for cookie / legacy bearer auth helpers."""

from __future__ import annotations

from unittest.mock import patch

from app.auth import cookie_auth


def test_legacy_token_body_auto_on_cross_origin_production():
    with patch.object(cookie_auth.settings, "ENVIRONMENT", "production"), patch.object(
        cookie_auth.settings, "FRONTEND_URL", "https://rajverse.me"
    ), patch.object(
        cookie_auth.settings, "BACKEND_URL", "https://zenith-backend-707i.onrender.com"
    ), patch.dict("os.environ", {"AUTH_LEGACY_TOKEN_BODY": ""}, clear=False):
        assert cookie_auth.legacy_token_body_enabled() is True


def test_legacy_token_body_off_for_first_party_subdomains():
    with patch.object(cookie_auth.settings, "ENVIRONMENT", "production"), patch.object(
        cookie_auth.settings, "FRONTEND_URL", "https://rajverse.me"
    ), patch.object(cookie_auth.settings, "BACKEND_URL", "https://api.rajverse.me"), patch.dict(
        "os.environ", {"AUTH_LEGACY_TOKEN_BODY": ""}, clear=False
    ):
        assert cookie_auth.legacy_token_body_enabled() is False


def test_cookie_domain_not_set_for_onrender_backend():
    with patch.dict(
        "os.environ",
        {"BACKEND_URL": "https://zenith-backend-707i.onrender.com", "AUTH_COOKIE_DOMAIN": ""},
        clear=False,
    ):
        assert cookie_auth._cookie_domain() is None
