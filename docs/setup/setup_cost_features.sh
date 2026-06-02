#!/bin/bash

# Cost Management Features - Quick Setup Script
# Run from project root: bash docs/setup_cost_features.sh

echo "🚀 Setting up Cost Management Features..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install scikit-learn==1.7.0 numpy==2.2.6 --quiet

# Check MongoDB
echo "🔍 Checking MongoDB connection..."
python -c "from app.database.mongo_client import mongodb_client; print('✅ MongoDB connected' if mongodb_client.client else '❌ MongoDB not connected')"

# Summary
echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Start Backend:  cd backend && uvicorn app.main:app --reload"
echo "2. Start Frontend: cd frontend && npm run dev"
echo "3. (Optional) Start Celery: cd backend && celery -A app.celery_worker worker --beat --loglevel=info"
echo ""
echo "🎯 New Features Available:"
echo "   • Budget Alerts - Set spending limits and get notifications"
echo "   • Cost Forecasting - Predict next month's costs using ML"
echo "   • Export Reports - Download cost data as CSV/JSON"
echo "   • Custom Date Presets - Quick filters (Last 7 days, Last month, YTD)"
echo "   • Cost Anomaly Detection - Alert when spending spikes unexpectedly"
echo ""
echo "📖 Documentation: docs/cost-analysis/COST_ANALYSIS_QUICKSTART.md"
