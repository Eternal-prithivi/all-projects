"""Unit tests for signup trust guards."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def test_is_disposable_email_detects_known_domains():
    from app.trust.signup_guards import is_disposable_email

    assert is_disposable_email("user@mailinator.com") is True
    assert is_disposable_email("user@gmail.com") is False
    assert is_disposable_email("") is False


def test_assert_email_allowed_rejects_disposable():
    from app.trust.signup_guards import assert_email_allowed

    with pytest.raises(HTTPException) as exc:
        assert_email_allowed("bot@yopmail.com")
    assert exc.value.status_code == 400
    assert "Disposable" in exc.value.detail


def test_assert_email_allowed_accepts_legitimate_domain():
    from app.trust.signup_guards import assert_email_allowed

    assert_email_allowed("user@gmail.com")


def test_assert_email_allowed_rejects_example_com_on_production():
    from app.trust.signup_guards import assert_email_allowed
    from app.utils.config import settings

    with patch.object(settings, "ENVIRONMENT", "production"):
        with pytest.raises(HTTPException) as exc:
            assert_email_allowed("user@example.com")
        assert exc.value.status_code == 400
        assert "Test email" in exc.value.detail


def test_assert_email_allowed_accepts_example_com_in_test_env():
    from app.trust.signup_guards import assert_email_allowed
    from app.utils.config import settings

    with patch.object(settings, "ENVIRONMENT", "test"):
        assert_email_allowed("user@example.com")


def test_is_test_signup_email_detects_reserved_domains():
    from app.trust.signup_guards import is_test_signup_email

    assert is_test_signup_email("verify_abc@example.com") is True
    assert is_test_signup_email("user@gmail.com") is False


@patch("app.database.mongo_client.get_database")
def test_email_verification_required_env_override_true(mock_get_db):
    from app.trust.signup_guards import email_verification_required
    from app.utils.config import settings

    mock_get_db.return_value["platform_settings"].find_one.return_value = {
        "require_email_verification": False,
    }
    with patch.object(settings, "REQUIRE_EMAIL_VERIFICATION", True), patch.object(
        settings, "ENVIRONMENT", "test"
    ):
        assert email_verification_required() is True


@patch("app.database.mongo_client.get_database")
def test_email_verification_required_env_override_false(mock_get_db):
    from app.trust.signup_guards import email_verification_required
    from app.utils.config import settings

    mock_get_db.return_value["platform_settings"].find_one.return_value = {
        "require_email_verification": True,
    }
    with patch.object(settings, "REQUIRE_EMAIL_VERIFICATION", False), patch.object(
        settings, "ENVIRONMENT", "production"
    ):
        assert email_verification_required() is False


@patch("app.database.mongo_client.get_database")
def test_email_verification_required_mongo_flag(mock_get_db):
    from app.trust.signup_guards import email_verification_required
    from app.utils.config import settings

    mock_get_db.return_value["platform_settings"].find_one.return_value = {
        "require_email_verification": True,
    }
    with patch.object(settings, "REQUIRE_EMAIL_VERIFICATION", None), patch.object(
        settings, "ENVIRONMENT", "test"
    ):
        assert email_verification_required() is True


@patch("app.database.mongo_client.get_database")
def test_email_verification_required_production_default(mock_get_db):
    from app.trust.signup_guards import email_verification_required
    from app.utils.config import settings

    mock_get_db.return_value["platform_settings"].find_one.return_value = {}
    with patch.object(settings, "REQUIRE_EMAIL_VERIFICATION", None), patch.object(
        settings, "ENVIRONMENT", "production"
    ):
        assert email_verification_required() is True


@patch("app.database.mongo_client.get_database")
def test_email_verification_required_staging_default(mock_get_db):
    from app.trust.signup_guards import email_verification_required
    from app.utils.config import settings

    mock_get_db.return_value["platform_settings"].find_one.return_value = {}
    with patch.object(settings, "REQUIRE_EMAIL_VERIFICATION", None), patch.object(
        settings, "ENVIRONMENT", "staging"
    ):
        assert email_verification_required() is True


@patch("app.database.mongo_client.get_database")
def test_email_verification_required_test_default_off(mock_get_db):
    from app.trust.signup_guards import email_verification_required
    from app.utils.config import settings

    mock_get_db.return_value["platform_settings"].find_one.return_value = {}
    with patch.object(settings, "REQUIRE_EMAIL_VERIFICATION", None), patch.object(
        settings, "ENVIRONMENT", "test"
    ):
        assert email_verification_required() is False


def test_verify_turnstile_noop_without_secret():
    from app.trust.signup_guards import verify_turnstile_token

    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("TURNSTILE_SECRET_KEY", None)
        verify_turnstile_token(None)


def test_verify_turnstile_rejects_missing_token_when_secret_set():
    from app.trust.signup_guards import verify_turnstile_token

    with patch.dict("os.environ", {"TURNSTILE_SECRET_KEY": "test-secret"}):
        with pytest.raises(HTTPException) as exc:
            verify_turnstile_token(None)
        assert exc.value.status_code == 400
        assert "CAPTCHA" in exc.value.detail


@patch("httpx.Client")
def test_verify_turnstile_accepts_valid_response(mock_client_cls):
    from app.trust.signup_guards import verify_turnstile_token

    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True}
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    with patch.dict("os.environ", {"TURNSTILE_SECRET_KEY": "test-secret"}):
        verify_turnstile_token("valid-token", "127.0.0.1")

    mock_client.post.assert_called_once()
