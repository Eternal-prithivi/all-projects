#!/bin/bash

# Quick Demo Mode Test Script
# This will help you verify DEMO_MODE is working

echo "════════════════════════════════════════════════════════"
echo "🎭 DEMO MODE QUICK TEST"
echo "════════════════════════════════════════════════════════"
echo ""

# Step 1: Check .env file
echo "📋 Step 1: Checking .env file..."
echo "────────────────────────────────────────────────────────"
cd backend
if grep -q "DEMO_MODE=true" .env 2>/dev/null; then
    echo "✅ Found: DEMO_MODE=true in .env"
elif grep -q "DEMO_MODE=false" .env 2>/dev/null; then
    echo "⚠️  Found: DEMO_MODE=false in .env"
    echo ""
    echo "   To enable demo mode, change it to:"
    echo "   DEMO_MODE=true"
elif grep -q "DEMO_MODE" .env 2>/dev/null; then
    echo "⚠️  Found DEMO_MODE but value unclear"
    echo "   Current line:"
    grep "DEMO_MODE" .env
else
    echo "❌ DEMO_MODE not found in .env"
    echo ""
    echo "   Add this line to backend/.env:"
    echo "   DEMO_MODE=true"
fi
echo ""

# Step 2: Test Python import
echo "📋 Step 2: Testing demo mode import..."
echo "────────────────────────────────────────────────────────"
cd ..
python3 << 'PYEOF'
import sys
sys.path.insert(0, 'backend')
try:
    from app.config.demo_mode import is_demo_mode, DEMO_MODE
    print(f"✅ Import successful!")
    print(f"   DEMO_MODE value: {DEMO_MODE}")
    print(f"   is_demo_mode(): {is_demo_mode()}")
    print("")
    if is_demo_mode():
        print("   🎭 Demo mode is ENABLED - will use mock data!")
        print("   💰 Cost: $0.00 (no real API calls)")
    else:
        print("   ⚠️  Demo mode is DISABLED - will use real APIs!")
        print("   💰 Cost: ~$0.10-0.20/day")
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF
echo ""

# Step 3: How to start backend with demo mode
echo "📋 Step 3: How to start backend..."
echo "────────────────────────────────────────────────────────"
echo "Run these commands to start backend with demo mode:"
echo ""
echo "  cd backend"
echo "  source ../venv/bin/activate"  
echo "  uvicorn app.main:app --reload"
echo ""
echo "Then in another terminal, run:"
echo "  python3 test_demo_mode.py"
echo ""

# Step 4: How to verify demo mode is working
echo "📋 Step 4: How to verify demo mode is working..."
echo "────────────────────────────────────────────────────────"
echo "When demo mode is working, you'll see:"
echo ""
echo "1. In test output:"
echo "   ✅ Demo Mode Enabled: True"
echo "   🎭 CONFIRMED: Using mock data"
echo ""
echo "2. In backend logs:"
echo "   🎭 DEMO MODE: Using mock data for AWS Cost Explorer (zero cost)"
echo ""
echo "3. In API responses:"
echo "   \"demo_mode\": true"
echo ""
echo "To watch for demo mode logs:"
echo "  tail -f logs/backend.log | grep 'DEMO MODE'"
echo ""

echo "════════════════════════════════════════════════════════"
echo "📊 SUMMARY"
echo "════════════════════════════════════════════════════════"
echo ""
echo "If DEMO_MODE=true in .env:"
echo "  ✅ NO real AWS/GCP/Azure API calls"
echo "  ✅ Uses mock/fake data"
echo "  ✅ Cost: $0.00"
echo ""
echo "If DEMO_MODE=false in .env:"
echo "  ⚠️  Makes real API calls"
echo "  ⚠️  Costs ~$0.10-0.20/day"
echo "  ✅ But has caching (97% savings!)"
echo ""
echo "════════════════════════════════════════════════════════"

