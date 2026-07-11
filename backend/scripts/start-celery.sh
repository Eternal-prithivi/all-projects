#!/bin/bash
# Start Celery worker + Beat for Zenith (run from anywhere).
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/dev-common.sh"
cd "$BACKEND_DIR"
zenith_ensure_celery
exec "$CELERY_BIN" -A app.celery_worker worker --beat --loglevel=info
