#!/bin/bash

# Quick check if demo mode will work when backend starts

echo "🔍 Checking Demo Mode Configuration..."
echo ""

cd "$(dirname "$0")/backend"

# Check .env file
echo "1️⃣  Checking .env file:"
if grep -q "DEMO_MODE=true" .env 2>/dev/null; then
    echo "   ✅ DEMO_MODE=true found in .env"
    EXPECTED="true"
elif grep -q "DEMO_MODE=false" .env 2>/dev/null; then
    echo "   ✅ DEMO_MODE=false found in .env"
    EXPECTED="false"
else
    echo "   ❌ DEMO_MODE not found in .env"
    exit 1
fi
echo ""

# Test if Python can load it
echo "2️⃣  Testing if Python can read it:"
cd ..
RESULT=$(source venv/bin/activate 2>/dev/null && cd backend && python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    from app.config.demo_mode import is_demo_mode
    print("true" if is_demo_mode() else "false")
except Exception as e:
    print(f"ERROR: {e}")
PYEOF
)

echo "   Python reads: DEMO_MODE=$RESULT"
echo "   Expected:     DEMO_MODE=$EXPECTED"
echo ""

if [ "$RESULT" = "$EXPECTED" ]; then
    echo "✅ SUCCESS! Demo mode is configured correctly!"
    echo ""
    if [ "$EXPECTED" = "true" ]; then
        echo "🎭 Demo mode is ENABLED"
        echo "   • Will use mock/fake data"
        echo "   • No real API calls"
        echo "   • Cost: $0.00"
        echo ""
        echo "   Backend logs will show:"
        echo "   🎭 DEMO MODE: Using mock data for [API Name] (zero cost)"
    else
        echo "⚠️  Demo mode is DISABLED"
        echo "   • Will use real AWS/GCP/Azure APIs"
        echo "   • With caching (97% savings)"
        echo "   • Cost: ~$0.10-0.20/day"
        echo ""
        echo "   To enable demo mode, change to:"
        echo "   DEMO_MODE=true"
    fi
else
    echo "❌ MISMATCH! Demo mode not loading correctly"
    echo ""
    echo "This shouldn't happen. The fix should have worked."
    echo "Result: $RESULT"
fi
echo ""
echo "════════════════════════════════════════════════════════"

