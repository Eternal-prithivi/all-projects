import sys
sys.path.insert(0, 'backend')
from backend.app.database.mongo_client import get_database

DB = get_database()

print("=== ALL VM Assignments ===")
assignments = list(DB["vm_assignments"].find({}))
for a in assignments:
    print(f"\nAssignment ID: {a.get('assignment_id')}")
    print(f"  User: {a.get('user_id')}")
    print(f"  VM: {a.get('vm_name')}")
    print(f"  Status: {a.get('status')}")
    print(f"  Assigned: {a.get('assigned_at')}")

print(f"\n=== Summary ===")
active = [a for a in assignments if a.get('status') == 'active']
print(f"Total assignments: {len(assignments)}")
print(f"Active assignments: {len(active)}")

if active:
    print("\nActive assignment details:")
    for a in active:
        print(f"  - {a.get('user_id')} → {a.get('vm_name')} ({a.get('assignment_id')})")
