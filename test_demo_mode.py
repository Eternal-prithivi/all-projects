#!/usr/bin/env python3
"""
Test script to verify DEMO_MODE is working correctly.
This will show you:
1. If demo mode is enabled
2. Test API calls return mock data
3. Confirm no real AWS/GCP/Azure APIs are called
"""

import requests
import json
from datetime import datetime, timedelta

print("=" * 60)
print("🎭 DEMO MODE VERIFICATION TEST")
print("=" * 60)
print()

# Backend URL
BASE_URL = "http://localhost:8000"

# Test 1: Check if demo mode is enabled
print("📋 Test 1: Checking Demo Mode Status")
print("-" * 60)
try:
    # Import the demo mode config
    import sys
    sys.path.insert(0, '/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/backend')
    from app.config.demo_mode import is_demo_mode, DEMO_MODE
    
    print(f"✅ Demo Mode Enabled: {is_demo_mode()}")
    print(f"   Environment Variable: DEMO_MODE={DEMO_MODE}")
    
    if is_demo_mode():
        print("   🎭 Using MOCK DATA (zero cost!)")
    else:
        print("   ⚠️  Using REAL APIs (costs money)")
    print()
except Exception as e:
    print(f"❌ Error checking demo mode: {e}")
    print()

# Test 2: Test AWS Cost Explorer API
print("📋 Test 2: AWS Cost Explorer API")
print("-" * 60)
try:
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    response = requests.get(
        f"{BASE_URL}/api/cost/aws",
        params={
            "start_date": start_date,
            "end_date": end_date,
            "granularity": "DAILY"
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Demo Mode in Response: {data.get('demo_mode', False)}")
        print(f"   Provider: {data.get('provider', 'N/A')}")
        print(f"   Data Points: {len(data.get('data', {}).get('ResultsByTime', []))}")
        
        if data.get('demo_mode'):
            print("   🎭 CONFIRMED: Using mock data (NO real AWS API call!)")
        else:
            print("   ⚠️  WARNING: Using real AWS API (costs $0.01 per call)")
    else:
        print(f"❌ API call failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    print()
except Exception as e:
    print(f"❌ Error: {e}")
    print()

# Test 3: Test GCP Costs API
print("📋 Test 3: GCP Cost API")
print("-" * 60)
try:
    response = requests.get(
        f"{BASE_URL}/api/cost/gcp",
        params={
            "start_date": start_date,
            "end_date": end_date
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Demo Mode in Response: {data.get('demo_mode', False)}")
        print(f"   Provider: {data.get('provider', 'N/A')}")
        
        if data.get('demo_mode'):
            print("   🎭 CONFIRMED: Using mock data (NO real GCP API call!)")
        else:
            print("   ⚠️  WARNING: Using real GCP API")
    else:
        print(f"❌ API call failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    print()
except Exception as e:
    print(f"❌ Error: {e}")
    print()

# Test 4: Test Azure Costs API
print("📋 Test 4: Azure Cost API")
print("-" * 60)
try:
    response = requests.get(
        f"{BASE_URL}/api/cost/azure",
        params={
            "start_date": start_date,
            "end_date": end_date
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Demo Mode in Response: {data.get('demo_mode', False)}")
        print(f"   Provider: {data.get('provider', 'N/A')}")
        
        if data.get('demo_mode'):
            print("   🎭 CONFIRMED: Using mock data (NO real Azure API call!)")
        else:
            print("   ⚠️  WARNING: Using real Azure API")
    else:
        print(f"❌ API call failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    print()
except Exception as e:
    print(f"❌ Error: {e}")
    print()

# Test 5: Check backend logs for demo mode messages
print("📋 Test 5: Checking Backend Logs for Demo Mode Messages")
print("-" * 60)
try:
    with open('/Users/a.prithiviraj/Documents/CloudResourceOptimizationPlatform/logs/backend.log', 'r') as f:
        logs = f.readlines()
        demo_logs = [line for line in logs if '🎭 DEMO MODE' in line or 'DEMO MODE' in line]
        
        if demo_logs:
            print("✅ Demo mode log messages found:")
            for log in demo_logs[-5:]:  # Show last 5
                print(f"   {log.strip()}")
        else:
            print("⚠️  No demo mode log messages found")
            print("   (This is expected if no API calls were made yet)")
    print()
except Exception as e:
    print(f"❌ Error reading logs: {e}")
    print()

# Final Summary
print("=" * 60)
print("📊 SUMMARY")
print("=" * 60)
print()
print("If you see '🎭 DEMO MODE' messages and 'demo_mode: true'")
print("in the API responses, then demo mode is working correctly!")
print()
print("✅ NO REAL API CALLS = $0.00 COST")
print()
print("To see live demo mode logs, run:")
print("  tail -f logs/backend.log | grep 'DEMO MODE'")
print()
print("=" * 60)

