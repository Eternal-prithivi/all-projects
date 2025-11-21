#!/bin/bash

echo "═══════════════════════════════════════════════════════"
echo "🚀 Starting Backend to Test Demo Mode"
echo "═══════════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")/backend"

echo "📋 Step 1: Checking .env file..."
if grep -q "DEMO_MODE=true" .env 2>/dev/null; then
    echo "✅ DEMO_MODE=true found in .env"
elif grep -q "DEMO_MODE=false" .env 2>/dev/null; then
    echo "✅ DEMO_MODE=false found in .env"
else
    echo "❌ DEMO_MODE not found in .env"
    echo ""
    echo "Add this line to backend/.env:"
    echo "DEMO_MODE=true"
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
exec uvicorn app.main:app --reload

