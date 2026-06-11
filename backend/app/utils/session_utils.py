"""Helpers for login sessions and client metadata."""

import json
import urllib.error
import urllib.request
from typing import Optional


def get_client_ip(request) -> str:
    """Resolve client IP from proxy headers or direct connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "Unknown"


def parse_user_agent(user_agent: Optional[str]) -> str:
    """Return a short human-readable device/browser label from User-Agent."""
    if not user_agent:
        return "Web browser"

    ua = user_agent.lower()

    if "edg/" in ua or "edge" in ua:
        browser = "Microsoft Edge"
    elif "chrome" in ua and "safari" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = "Browser"

    if "iphone" in ua:
        return f"{browser} on iPhone"
    if "ipad" in ua:
        return f"{browser} on iPad"
    if "android" in ua:
        return f"{browser} on Android"
    if "mac os" in ua or "macintosh" in ua:
        return f"{browser} on macOS"
    if "windows" in ua:
        return f"{browser} on Windows"
    if "linux" in ua:
        return f"{browser} on Linux"

    return browser


def resolve_geo_location(ip: str, timeout: float = 2.5) -> str:
    """Best-effort city/country from IP (free tier ip-api.com). Falls back gracefully."""
    if not ip or ip in ("Unknown", "127.0.0.1", "::1", "localhost"):
        return "Local network"
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return "Local network"
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") == "success":
            city = (data.get("city") or "").strip()
            country = (data.get("country") or "").strip()
            parts = [p for p in (city, country) if p]
            if parts:
                return ", ".join(parts)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        pass
    return "Unknown location"


def fingerprint_display(device_fingerprint: Optional[str]) -> Optional[str]:
    """Short label for UI (first 8 hex chars of SHA-256)."""
    if not device_fingerprint or len(device_fingerprint) < 8:
        return None
    return device_fingerprint[:8].upper()
