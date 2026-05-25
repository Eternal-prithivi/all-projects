"""Unit tests for password recovery helpers."""

from app.auth.password_reset_service import (
    identifier_matches_account,
    normalize_phone_e164,
)
from app.utils import sms_notifications


def test_normalize_phone_e164_international():
    assert normalize_phone_e164("+919876543210") == "+919876543210"
    assert normalize_phone_e164("+1 555 123 4567") == "+15551234567"


def test_normalize_phone_e164_india_ten_digit():
    assert normalize_phone_e164("9876543210") == "+919876543210"


def test_normalize_phone_e164_invalid():
    assert normalize_phone_e164("") is None
    assert normalize_phone_e164("abc") is None


def test_us_sender_to_india_recipient_hint(monkeypatch):
    monkeypatch.setattr(sms_notifications, "TWILIO_MESSAGING_SERVICE_SID", "")
    monkeypatch.setattr(sms_notifications, "TWILIO_PHONE_NUMBER", "+16362095837")
    hint = sms_notifications.check_sms_route_compatible("+918807730239")
    assert hint is not None
    assert "India" in hint or "+91" in hint


def test_identifier_matches_account():
    user = {
        "username": "alice",
        "email": "alice@example.com",
        "recovery_email": "recover@example.com",
    }
    assert identifier_matches_account(user, "alice")
    assert identifier_matches_account(user, "alice@example.com")
    assert identifier_matches_account(user, "recover@example.com")
    assert not identifier_matches_account(user, "stranger@example.com")
    assert not identifier_matches_account(user, "bob")
