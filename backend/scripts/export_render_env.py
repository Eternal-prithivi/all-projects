#!/usr/bin/env python3
"""
Build one .env file for Render → Environment (bulk upload).

Merge rules:
  1. Start with render-env-from-paste.env (your Render paste — fallback)
  2. Overwrite with backend/.env (your laptop file wins on same key)
  3. Apply production overrides (rajverse.me, Render URL, etc.)

Usage (from repo root):
  python3 backend/scripts/export_render_env.py

Output: render-env-paste.env (gitignored)
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PASTE_SOURCE = REPO_ROOT / "render-env-from-paste.env"
LOCAL_SOURCE = REPO_ROOT / "backend" / ".env"
OUTPUT = REPO_ROOT / "render-env-paste.env"

# Always set for production deploy (wins over both sources)
OVERRIDES = {
    "ENVIRONMENT": "production",
    "DEMO_MODE": "false",
    "FRONTEND_URL": "https://rajverse.me",
    "BACKEND_URL": "https://zenith-backend-707.onrender.com",
    "PUBLIC_API_URL": "https://zenith-backend-707.onrender.com",
    "USE_REAL_METRICS": "false",
}

OPTIONAL_DEFAULTS = {
    "RAZORPAY_WEBHOOK_SECRET": "",
    "CORS_ALLOWED_ORIGINS": "",
    "GCP_SERVICE_ACCOUNT_JSON_PATH": "/etc/secrets/gcp-key.json",
    "SENTRY_DSN": "",
    "SENTRY_TRACES_SAMPLE_RATE": "0.1",
    "GOOGLE_OAUTH_CLIENT_ID": "",
    "GOOGLE_OAUTH_CLIENT_SECRET": "",
}

SKIP_KEYS = {"API_PORT", "REDIS_URL"}


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        out[key] = strip_quotes(val)
    return out


def format_line(key: str, val: str) -> str:
    if val == "":
        return f"{key}="
    if re.search(r"[\s#=\"']", val):
        return f'{key}="{val}"'
    return f"{key}={val}"


def main() -> None:
    if not LOCAL_SOURCE.is_file():
        raise SystemExit(f"Missing {LOCAL_SOURCE}")

    pasted = parse_env(PASTE_SOURCE)
    local = parse_env(LOCAL_SOURCE)

    # paste first, then local wins, then production overrides
    merged: dict[str, str] = {}
    merged.update(pasted)
    merged.update(local)
    merged.update(OVERRIDES)

    for key, default in OPTIONAL_DEFAULTS.items():
        merged.setdefault(key, default)

    only_paste = sorted(set(pasted) - set(local))
    only_local = sorted(set(local) - set(pasted))
    overlap = sorted(set(pasted) & set(local))

    lines = [
        "# Upload to Render → zenith-backend → Environment (.env format, NOT CSV)",
        "# Merge: backend/.env wins on overlap; paste-only keys kept from render-env-from-paste.env",
        "# DO NOT COMMIT",
        "",
    ]
    for key in sorted(merged.keys()):
        if key in SKIP_KEYS:
            continue
        lines.append(format_line(key, merged[key]))

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(merged)} variables to:\n  {OUTPUT}\n")
    print("Merge summary:")
    print(f"  From paste only (used as-is):     {len(only_paste)} keys")
    print(f"  From backend/.env only:           {len(only_local)} keys")
    print(f"  In both (.env value used):        {len(overlap)} keys")
    if only_paste:
        print(f"  Paste-only keys: {', '.join(only_paste)}")
    if only_local:
        print(f"  .env-only keys:  {', '.join(only_local)}")
    print("\nRender duplicate error fix:")
    print("  Delete ALL existing env vars on Render first, THEN upload this .env file.")
    print("  Use .env upload — not CSV.")


if __name__ == "__main__":
    main()
