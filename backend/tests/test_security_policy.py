from app.security.security_policy import (
    DEFAULT_SECURITY_PREFS,
    resolve_upload_encryption_defaults,
)


def test_resolve_upload_encryption_always_ask():
    result = resolve_upload_encryption_defaults("user", always_ask_encryption=True)
    assert result["needs_encryption_choice"] is True


def test_resolve_upload_encryption_explicit_server():
    result = resolve_upload_encryption_defaults(
        "user",
        explicit_encryption="server-side",
    )
    assert result["needs_encryption_choice"] is False
    assert result["default_encryption_method"] == "server-side"


def test_default_security_prefs_keys():
    assert "stale_file_days" in DEFAULT_SECURITY_PREFS
    assert DEFAULT_SECURITY_PREFS["ml_assisted_scan"] is True
