import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.mongo_client import get_database

DB = get_database()

print("🧹 Cleaning up all VM assignments...")
print()

# Get current state
all_assignments = list(DB["vm_assignments"].find({}))
active_count = len([a for a in all_assignments if a.get('status') == 'active'])

print(f"📊 Current state:")
print(f"   Total assignments: {len(all_assignments)}")
print(f"   Active assignments: {active_count}")
print()

# Release all active assignments
result = DB["vm_assignments"].update_many(
    {"status": "active"},
    {"$set": {"status": "released"}}
)

print(f"✅ Released {result.modified_count} active assignments")
print()

# Verify
remaining_active = DB["vm_assignments"].count_documents({"status": "active"})
print(f"🎯 Remaining active assignments: {remaining_active}")
print()
print("✨ Demo environment is now clean - all assignments released!")
print("   Cluster health should now show '0 Active Users'")
