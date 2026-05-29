#!/bin/bash
# Interactive backend for DEMO_MODE verification (foreground uvicorn).

set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/dev-common.sh"

echo "═══════════════════════════════════════════════════════"
echo "🚀 Starting Backend to Test Demo Mode"
echo "═══════════════════════════════════════════════════════"
echo ""

cd "$BACKEND_DIR"

echo "📋 Step 1: Checking .env file..."
if grep -qiE '^DEMO_MODE[[:space:]]*=[[:space:]]*true' .env 2>/dev/null; then
  echo "✅ DEMO_MODE=true found in .env"
elif grep -qiE '^DEMO_MODE[[:space:]]*=[[:space:]]*false' .env 2>/dev/null; then
  echo "✅ DEMO_MODE=false found in .env"
else
  echo "❌ DEMO_MODE not found in .env"
  echo ""
  echo "Add this line to backend/.env:"
  echo "DEMO_MODE=true"
  exit 1
fi

zenith_ensure_python_tooling

echo ""
echo "📋 Step 2: Starting backend on http://localhost:${BACKEND_PORT}"
echo ""
echo "In another terminal:"
echo "  curl 'http://localhost:${BACKEND_PORT}/api/cost/aws?start_date=2025-01-01&end_date=2025-01-31' | grep demo_mode"
echo ""
echo "Press Ctrl+C to stop"
echo "───────────────────────────────────────────────────────"
echo ""

exec "$UVICORN_BIN" app.main:app --reload --port "$BACKEND_PORT"
