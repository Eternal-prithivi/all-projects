#!/bin/bash

# Move testing/demo files to development folder
mv TEST_DEMO_MODE_NOW.txt docs/development/ 2>/dev/null
mv CACHE_VERDICT.txt docs/development/ 2>/dev/null
mv check_demo_mode.sh docs/development/ 2>/dev/null
mv test_demo_mode.py docs/development/ 2>/dev/null
mv test_demo_now.sh docs/development/ 2>/dev/null
mv quick_demo_test.sh docs/development/ 2>/dev/null
mv execute_project.txt docs/development/ 2>/dev/null

# Move deployment scripts to deployment folder
mv pre-deploy-check.sh docs/deployment/ 2>/dev/null

# Move startup scripts to scripts subfolder under development
mkdir -p docs/development/scripts 2>/dev/null
mv start_all.sh docs/development/scripts/ 2>/dev/null
mv start_backend_test.sh docs/development/scripts/ 2>/dev/null
mv start_celery_redis.sh docs/development/scripts/ 2>/dev/null
mv start_frontend_backend.sh docs/development/scripts/ 2>/dev/null

# Move Python test scripts to development
mv check_assignments.py docs/development/ 2>/dev/null
mv check_subscription.py docs/development/ 2>/dev/null
mv test_mongo.py docs/development/ 2>/dev/null

echo "✅ Documentation organized!"
