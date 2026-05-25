#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
UVICORN_BIN="$PROJECT_ROOT/venv/bin/uvicorn"

echo "═══════════════════════════════════════════════════════"
echo "🚀 Starting Backend to Test Demo Mode"
echo "═══════════════════════════════════════════════════════"
echo ""

cd "$BACKEND_DIR"

echo "📋 Step 1: Checking .env file..."
if grep -qiE '^DEMO_MODE[[:space:]]*=[[:space:]]*true' .env 2>/dev/null; then
    echo "✅ DEMO_MODE=True found in .env"
elif grep -qiE '^DEMO_MODE[[:space:]]*=[[:space:]]*false' .env 2>/dev/null; then
    echo "✅ DEMO_MODE=False found in .env"
else
    echo "❌ DEMO_MODE not found in .env"
    echo ""
    echo "Add this line to backend/.env:"
    echo "DEMO_MODE=true"
    exit 1
fi

if [ ! -x "$UVICORN_BIN" ]; then
    echo "❌ Missing executable: $UVICORN_BIN"
    echo "Run this first:"
    echo "  $PROJECT_ROOT/venv/bin/python -m pip install -r $BACKEND_DIR/requirements.txt"
    exit 1
fi

echo ""
echo "📋 Step 2: Starting backend..."
echo "This will start the backend on http://localhost:8000"
echo ""
echo "Once started, open a NEW terminal and run:"
echo "  curl 'http://localhost:8000/api/cost/aws?start_date=2025-01-01&end_date=2025-01-31' | grep demo_mode"
echo ""
echo "You should see:"
echo "  \"demo_mode\": true    ← if DEMO_MODE=true"
echo "  \"demo_mode\": false   ← if DEMO_MODE=false"
echo ""
echo "Press Ctrl+C to stop the backend"
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Start uvicorn using the standard method
exec "$UVICORN_BIN" app.main:app --reload
