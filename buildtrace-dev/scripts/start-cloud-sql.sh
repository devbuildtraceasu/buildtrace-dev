#!/bin/bash
# Start Cloud SQL instance
# Use this script to restart the database after stopping it

set -e

PROJECT_ID="buildtrace-dev"
INSTANCE_NAME="buildtrace-dev-db"
REGION="us-west2"

echo "🔄 Starting Cloud SQL instance: ${INSTANCE_NAME}..."
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo ""

gcloud sql instances patch ${INSTANCE_NAME} \
    --project=${PROJECT_ID} \
    --activation-policy=ALWAYS

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Cloud SQL instance started successfully!"
    echo ""
    echo "⏳ Note: It may take 2-5 minutes for the instance to be fully available."
    echo ""
    echo "📊 To check status:"
    echo "   gcloud sql instances describe ${INSTANCE_NAME} --project=${PROJECT_ID}"
    echo ""
    echo "🔍 To check if it's ready:"
    echo "   gcloud sql instances describe ${INSTANCE_NAME} --project=${PROJECT_ID} | grep state"
    echo "   (Look for state: RUNNABLE)"
else
    echo ""
    echo "❌ Failed to start instance. Check your permissions and try again."
    exit 1
fi
