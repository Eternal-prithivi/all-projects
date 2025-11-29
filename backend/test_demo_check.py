from app.utils.config import settings
from app.config.demo_mode import DEMO_MODE, is_demo_mode

print("DEMO_MODE Status Check")
print("=" * 40)
print(f"From settings: {settings.DEMO_MODE}")
print(f"From module: {DEMO_MODE}")
print(f"is_demo_mode(): {is_demo_mode()}")
print("=" * 40)

if is_demo_mode():
    print("✅ DEMO MODE ACTIVE - Using mock data")
else:
    print("❌ DEMO MODE DISABLED - Using real APIs")
