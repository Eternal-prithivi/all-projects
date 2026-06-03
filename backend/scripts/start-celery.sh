#!/usr/bin/env sh
# Start Celery worker + Beat for Zenith (run from backend/)
set -e
cd "$(dirname "$0")/.."
if [ -f ../venv/bin/activate ]; then
  # shellcheck source=/dev/null
  . ../venv/bin/activate
fi
exec celery -A app.celery_worker worker --beat --loglevel=info
