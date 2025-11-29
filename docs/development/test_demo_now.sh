#!/bin/bash

echo "═══════════════════════════════════════════════════════"
echo "🎭 DEMO MODE VERIFICATION TEST"
echo "═══════════════════════════════════════════════════════"
echo ""

cd "$(dirname "$0")"

# Test with venv Python
echo "🔍 Testing with virtual environment..."
echo ""

# Use venv Python directly (bypassing activation issues)
VENV_PYTHON="/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/venv/bin/python3"

if [ -x "$VENV_PYTHON" ]; then
    cd backend
    $VENV_PYTHON test_demo_simple.py
    EXIT_CODE=$?
    cd ..
    
    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Test completed successfully!"
    else
        echo "❌ Test failed with exit code $EXIT_CODE"
    fi
else
    echo "❌ Virtual environment not found at: $VENV_PYTHON"
    echo ""
    echo "Please ensure your venv is set up correctly."
fi

echo ""
echo "═══════════════════════════════════════════════════════"

