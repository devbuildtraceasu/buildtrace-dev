#!/bin/bash

# DEPRECATED: This script is deprecated in favor of deploy-branch.sh
# Please use ./gcp/scripts/deploy-branch.sh instead
# This script will be removed in a future version

echo "⚠️  WARNING: deploy-working.sh is DEPRECATED"
echo "🔄 Please use ./gcp/scripts/deploy-branch.sh instead"
echo "📖 See ./gcp/scripts/DEPLOYMENT_GUIDE.md for current deployment instructions"
echo ""
echo "Continuing with legacy deployment in 5 seconds..."
sleep 5

# Working deployment script for BuildTrace Overlay
# This uses local Docker build + Artifact Registry push approach

set -e

# Load environment variables from .env
if [ -f ".env" ]; then
    echo "📋 Loading environment variables from .env..."
    set -o allexport
    source .env
    set +o allexport
else
    echo "❌ .env file not found!"
    exit 1
fi

# Check if required variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in .env!"
    exit 1
fi

PROJECT_ID="buildtrace"
SERVICE_NAME="buildtrace-overlay"
REGION="us-central1"
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}:latest"

echo "🏗️  Building Docker image with AMD64 platform..."
docker build --platform linux/amd64 -f gcp/deployment/Dockerfile -t ${SERVICE_NAME}:latest .

echo "🏷️  Tagging image for Artifact Registry..."
docker tag ${SERVICE_NAME}:latest ${IMAGE_NAME}

echo "📤 Pushing image to Artifact Registry..."
docker push ${IMAGE_NAME}

echo "🚀 Deploying to Cloud Run..."
echo "🔧 Environment variables:"
echo "   FLASK_ENV=production"
echo "   OPENAI_API_KEY=sk-***[HIDDEN]"
echo "   OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o}"
echo "   DEFAULT_DPI=${DEFAULT_DPI:-300}"
echo "   DEBUG_MODE=${DEBUG_MODE:-false}"

gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --memory 32Gi \
  --cpu 8 \
  --timeout 3600 \
  --concurrency 1 \
  --max-instances 10 \
  --allow-unauthenticated \
  --add-cloudsql-instances=buildtrace:us-central1:buildtrace-postgres \
  --set-env-vars="FLASK_ENV=production,ENVIRONMENT=production,INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres,DB_USER=buildtrace_user,DB_NAME=buildtrace_db,GCS_BUCKET_NAME=buildtrace-storage,DB_PASS=BuildTrace2024SecurePassword,OPENAI_API_KEY=${OPENAI_API_KEY},OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o},DEFAULT_DPI=${DEFAULT_DPI:-300},DEBUG_MODE=${DEBUG_MODE:-false},MAX_CONTENT_LENGTH=73400320"

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://${SERVICE_NAME}-123644909590.${REGION}.run.app"