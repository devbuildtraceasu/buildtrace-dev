#!/bin/bash
# Stop Cloud SQL instance to save costs
# WARNING: This will stop the database. All services using it will fail until restarted.

set -e

PROJECT_ID="buildtrace-dev"
INSTANCE_NAME="buildtrace-dev-db"
REGION="us-west2"

echo "⚠️  WARNING: This will STOP the Cloud SQL instance: ${INSTANCE_NAME}"
echo "   All services using this database will fail until the instance is restarted."
echo ""
read -p "Are you sure you want to stop the instance? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled. Instance not stopped."
    exit 0
fi

echo ""
echo "🛑 Stopping Cloud SQL instance: ${INSTANCE_NAME}..."
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo ""

gcloud sql instances patch ${INSTANCE_NAME} \
    --project=${PROJECT_ID} \
    --activation-policy=NEVER

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Cloud SQL instance stopped successfully!"
    echo ""
    echo "📊 To check status:"
    echo "   gcloud sql instances describe ${INSTANCE_NAME} --project=${PROJECT_ID}"
    echo ""
    echo "🔄 To restart later:"
    echo "   gcloud sql instances patch ${INSTANCE_NAME} --project=${PROJECT_ID} --activation-policy=ALWAYS"
    echo ""
    echo "💰 Cost savings: Instance will not be charged while stopped (except for storage)."
else
    echo ""
    echo "❌ Failed to stop instance. Check your permissions and try again."
    exit 1
fi
