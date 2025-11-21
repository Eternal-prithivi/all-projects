#!/usr/bin/env python3
"""Simple demo mode test - run this with: python3 test_demo_simple.py"""

from app.config.demo_mode import is_demo_mode, DEMO_MODE

print("═══════════════════════════════════════")
print("🎭 DEMO MODE VERIFICATION")
print("═══════════════════════════════════════")
print(f"DEMO_MODE = {DEMO_MODE}")
print(f"is_demo_mode() = {is_demo_mode()}")
print("")

if is_demo_mode():
    print("✅ WORKING! Using mock data")
    print("   💰 Cost: $0.00 (no real API calls)")
    print("   🎭 All API responses will have 'demo_mode': true")
else:
    print("⚠️  DISABLED - Using real APIs")
    print("   💰 Cost: ~$0.10-0.20/day (with caching)")
    print("   📊 API responses will have 'demo_mode': false")

print("═══════════════════════════════════════")

