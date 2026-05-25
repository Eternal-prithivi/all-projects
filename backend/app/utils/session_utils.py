"""Helpers for login sessions and client metadata."""

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
