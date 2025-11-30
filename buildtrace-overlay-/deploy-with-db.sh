#!/bin/bash

# Deploy to Cloud Run with database environment variables
SERVICE_NAME=${1:-buildtrace-overlay}
REGION=${2:-us-central1}
PROJECT_ID=${3:-buildtrace}

echo "🚀 Deploying $SERVICE_NAME to Cloud Run with database enabled..."

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="USE_DATABASE=true" \
  --set-env-vars="USE_GCS=true" \
  --set-env-vars="USE_CLOUD_TASKS=true" \
  --set-env-vars="DB_USER=buildtrace_user" \
  --set-env-vars="DB_NAME=buildtrace_db" \
  --set-env-vars="INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres" \
  --set-secrets="DB_PASS=buildtrace-db-password:latest" \
  --add-cloudsql-instances="buildtrace:us-central1:buildtrace-postgres" \
  --cpu=1 \
  --memory=2Gi \
  --timeout=3600 \
  --max-instances=10 \
  --port=8080

echo "✅ Deployment complete!"
echo ""
echo "🔧 After deployment, run the database migration:"
echo "curl -X POST https://$SERVICE_NAME-hash-uc.a.run.app/admin/migrate-auth"
echo ""
echo "🔍 Check configuration with:"
echo "curl https://$SERVICE_NAME-hash-uc.a.run.app/admin/debug"