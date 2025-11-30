#!/bin/bash

# Branch-specific deployment script for BuildTrace Overlay
# Deploys each Git branch to its own Cloud Run service with a unique URL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌿 Branch-Specific Cloud Run Deployment${NC}"
echo "========================================="

# Load environment variables from .env
if [ -f ".env" ]; then
    echo -e "${GREEN}📋 Loading environment variables from .env...${NC}"
    set -o allexport
    source .env
    set +o allexport
else
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi

# Check if required variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not found in .env!${NC}"
    exit 1
fi

# Get current Git branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}📍 Current branch: ${YELLOW}$BRANCH${NC}"

# Sanitize branch name for Cloud Run (lowercase, replace / and _ with -)
SANITIZED_BRANCH=$(echo $BRANCH | sed 's/\//-/g' | sed 's/_/-/g' | tr '[:upper:]' '[:lower:]')

# Project configuration
PROJECT_ID="buildtrace"
REGION="us-central1"

# Generate service name based on branch
if [ "$BRANCH" = "main" ]; then
    SERVICE_NAME="buildtrace-overlay"
    echo -e "${GREEN}✅ Deploying to production service${NC}"
else
    SERVICE_NAME="buildtrace-overlay-${SANITIZED_BRANCH}"
    echo -e "${YELLOW}🔧 Deploying to branch service: $SERVICE_NAME${NC}"
fi

# Generate unique image tag for this branch
IMAGE_TAG="${SANITIZED_BRANCH}-$(date +%Y%m%d-%H%M%S)"
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}:${IMAGE_TAG}"
IMAGE_LATEST="us-central1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}:latest"

echo ""
echo -e "${BLUE}🏗️  Building Docker image...${NC}"
echo "   Platform: linux/amd64"
echo "   Tag: $IMAGE_TAG"
docker build --platform linux/amd64 -f gcp/deployment/Dockerfile -t ${SERVICE_NAME}:${IMAGE_TAG} .

echo ""
echo -e "${BLUE}🏷️  Tagging image for Artifact Registry...${NC}"
docker tag ${SERVICE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}
docker tag ${SERVICE_NAME}:${IMAGE_TAG} ${IMAGE_LATEST}

echo ""
echo -e "${BLUE}📤 Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}
docker push ${IMAGE_LATEST}

echo ""
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
echo -e "${YELLOW}🔧 Configuration:${NC}"
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Memory: 32Gi"
echo "   CPU: 8"
echo "   Timeout: 3600s"
echo ""
echo -e "${YELLOW}🔑 Environment Variables:${NC}"
echo "   FLASK_ENV=production"
echo "   ENVIRONMENT=production"
echo "   BRANCH=$BRANCH"
echo "   OPENAI_API_KEY=sk-***[HIDDEN]"
echo "   OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o}"

# Deploy to Cloud Run
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
  --set-env-vars="FLASK_ENV=production,ENVIRONMENT=production,BRANCH=${BRANCH},INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres,DB_USER=buildtrace_user,DB_NAME=buildtrace_db,GCS_BUCKET_NAME=buildtrace-storage,OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o},DEFAULT_DPI=${DEFAULT_DPI:-300},DEBUG_MODE=${DEBUG_MODE:-false},MAX_CONTENT_LENGTH=73400320,USE_CLOUD_TASKS=true" \
  --set-secrets="DB_PASS=buildtrace-db-password:latest,OPENAI_API_KEY=openai-api-key:latest,GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format='value(status.url)' 2>/dev/null || echo "")

echo ""
echo "========================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "========================================="
echo -e "${BLUE}📍 Branch:${NC} ${YELLOW}$BRANCH${NC}"
echo -e "${BLUE}🏷️  Service:${NC} ${YELLOW}$SERVICE_NAME${NC}"
echo -e "${BLUE}🐳 Image:${NC} ${YELLOW}$IMAGE_TAG${NC}"
if [ -n "$SERVICE_URL" ]; then
    echo -e "${BLUE}🌐 URL:${NC} ${GREEN}$SERVICE_URL${NC}"
else
    echo -e "${BLUE}🌐 URL:${NC} ${GREEN}https://${SERVICE_NAME}-123644909590.${REGION}.run.app${NC}"
fi
echo "========================================="

# Additional info for non-main branches
if [ "$BRANCH" != "main" ]; then
    echo ""
    echo -e "${YELLOW}📝 Branch Deployment Notes:${NC}"
    echo "   • This is a branch-specific deployment"
    echo "   • Service will remain active until manually deleted"
    echo "   • To delete this branch deployment, run:"
    echo -e "     ${BLUE}gcloud run services delete ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID}${NC}"
    echo ""
fi