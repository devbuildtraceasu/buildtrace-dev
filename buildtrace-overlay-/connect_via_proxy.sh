#!/bin/bash

echo "🔌 Setting up Cloud SQL Proxy connection..."

# Step 1: Install Cloud SQL Proxy (if not already installed)
if ! command -v cloud_sql_proxy &> /dev/null; then
    echo "📥 Installing Cloud SQL Proxy..."
    wget https://dl.google.com/cloudsql/cloud_sql_proxy.darwin.amd64 -O cloud_sql_proxy
    chmod +x cloud_sql_proxy
    sudo mv cloud_sql_proxy /usr/local/bin
fi

# Step 2: Start Cloud SQL Proxy in the background
echo "🚀 Starting Cloud SQL Proxy..."
cloud_sql_proxy -instances=buildtrace:us-central1:buildtrace-postgres=tcp:5432 &
PROXY_PID=$!

# Wait for proxy to start
sleep 3

echo "✅ Cloud SQL Proxy started (PID: $PROXY_PID)"
echo "🔗 You can now connect to localhost:5432"
echo ""
echo "To connect with psql:"
echo "PGPASSWORD='BuildTrace2024SecurePassword' psql -h localhost -p 5432 -U buildtrace_user -d buildtrace_db"
echo ""
echo "To stop the proxy later, run: kill $PROXY_PID"
echo ""

# Keep the script running to maintain the proxy
echo "Press Ctrl+C to stop the proxy..."
wait $PROXY_PID