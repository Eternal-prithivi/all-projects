#!/bin/bash
# Dev uvicorn — watches app/ only (avoids .venv reload loops after pip install).
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/dev-common.sh"
cd "$BACKEND_DIR"
zenith_ensure_python_tooling
exec "$UVICORN_BIN" app.main:app "${UVICORN_DEV_ARGS[@]}" --host 0.0.0.0 --port "${BACKEND_PORT}"
