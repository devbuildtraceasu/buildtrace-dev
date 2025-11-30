#!/bin/bash

# Set environment variables for production mode with database enabled
export ENVIRONMENT=production
export USE_DATABASE=true
export USE_GCS=true
export USE_CLOUD_TASKS=true

# Database configuration (update these with your actual values)
export DB_USER=buildtrace_user
export DB_PASS=${DB_PASS:-"your-database-password"}
export DB_NAME=buildtrace_db
export INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres

# Optional: Cloud SQL Auth Proxy (if using proxy instead of unix socket)
# export USE_CLOUD_SQL_AUTH_PROXY=true

echo "✅ Production environment variables set:"
echo "ENVIRONMENT=$ENVIRONMENT"
echo "USE_DATABASE=$USE_DATABASE"
echo "USE_GCS=$USE_GCS"
echo "USE_CLOUD_TASKS=$USE_CLOUD_TASKS"
echo "DB_USER=$DB_USER"
echo "DB_NAME=$DB_NAME"
echo "INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME"

echo ""
echo "Now run your app with: python app.py"
echo "Or source this file: source set_production_env.sh"