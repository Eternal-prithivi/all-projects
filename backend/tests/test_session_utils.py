"""Tests for session geo and fingerprint helpers."""

from app.utils.session_utils import (
    fingerprint_display,
    parse_user_agent,
    resolve_geo_location,
)


def test_resolve_geo_localhost():
    assert resolve_geo_location("127.0.0.1") == "Local network"


def test_resolve_geo_private_range():
    assert resolve_geo_location("192.168.1.10") == "Local network"


def test_fingerprint_display_short():
    fp = "a" * 64
    assert fingerprint_display(fp) == "AAAAAAAA"


def test_parse_user_agent_chrome():
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    label = parse_user_agent(ua)
    assert "Chrome" in label
