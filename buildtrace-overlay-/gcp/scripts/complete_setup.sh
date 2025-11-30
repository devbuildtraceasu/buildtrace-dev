#!/bin/bash

echo "BuildTrace Database Setup - Final Steps"
echo "========================================"
echo ""

# 1. Check if Cloud SQL instance is ready
echo "Checking Cloud SQL instance status..."
STATUS=$(gcloud sql instances describe buildtrace-postgres --project=buildtrace --format="value(state)")

if [ "$STATUS" != "RUNNABLE" ]; then
    echo "❌ Cloud SQL instance is still being created (Status: $STATUS)"
    echo "Please wait a few more minutes and run this script again."
    exit 1
fi

echo "✅ Cloud SQL instance is ready!"
echo ""

# 2. Create database and user
echo "Creating database and user..."
./setup_database.sh

echo ""
echo "========================================"
echo "Next steps:"
echo ""
echo "1. Update your .env file with the database password you just set"
echo "   Edit: .env"
echo ""
echo "2. Start the Cloud SQL Proxy in a separate terminal:"
echo "   ./cloud-sql-proxy --instances=buildtrace:us-central1:buildtrace-postgres=tcp:5432"
echo ""
echo "3. Install Python dependencies if not already done:"
echo "   pip install -r requirements.txt"
echo ""
echo "4. Initialize the database tables:"
echo "   python migrations/init_database.py"
echo ""
echo "5. Test the connection:"
echo "   python -c 'from database import db_manager; print(\"Connected!\" if db_manager.engine else \"Failed\")'"
echo ""
echo "========================================"