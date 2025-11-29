#!/usr/bin/env python3
"""Quick script to check user subscription in MongoDB"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

MONGODB_URL = os.getenv('MONGODB_URL')
client = MongoClient(MONGODB_URL)
db = client['cloud_optimization']

print("\n=== Checking Your Subscription ===\n")

# Replace with your username
username = input("Enter your username: ")

# Check subscription
subscription = db['subscriptions'].find_one({"user_id": username})
print(f"\n📋 Subscription: {subscription}")

# Check user limits
user = db['users'].find_one({"username": username})
if user:
    print(f"\n👤 User Limits:")
    print(f"   Plan ID: {user.get('plan_id', 'free')}")
    print(f"   VM Limit: {user.get('vm_limit', 2)} VMs")
    print(f"   Storage Limit: {user.get('storage_limit_gb', 10)} GB")

# Check payment orders
orders = list(db['payment_orders'].find({"user_id": username}).sort("created_at", -1).limit(3))
print(f"\n💳 Recent Orders: {len(orders)} found")
for order in orders:
    print(f"   - {order['plan_id']} ({order['status']}) - ₹{order['amount']}")

client.close()
