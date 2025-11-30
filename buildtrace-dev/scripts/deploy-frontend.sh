#!/bin/bash
# Frontend-Only Deployment Script

set -e  # Exit on error

echo "================================================================================"
echo "BUILTRACE FRONTEND DEPLOYMENT"
echo "================================================================================"
echo ""

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-buildtrace-dev}"
REGION="${GCP_REGION:-us-west2}"
IMAGE_REGISTRY="gcr.io/${PROJECT_ID}"

echo "Configuration:"
echo "  Project ID: ${PROJECT_ID}"
echo "  Region: ${REGION}"
echo "  Image Registry: ${IMAGE_REGISTRY}"
echo ""

# Pre-deployment checks
echo "================================================================================"
echo "Pre-Deployment Checks"
echo "================================================================================"

if [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: Must run from buildtrace-dev directory"
    exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }
command -v gcloud >/dev/null 2>&1 || { echo "❌ gcloud not found"; exit 1; }

echo "✓ Pre-deployment checks passed"
echo ""

# Get backend URL
echo "================================================================================"
echo "Fetching Backend URL"
echo "================================================================================"

BACKEND_URL=$(gcloud run services describe buildtrace-backend \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format='value(status.url)' 2>/dev/null || echo "https://buildtrace-backend-136394139608.us-west2.run.app")

echo "Backend URL: ${BACKEND_URL}"
echo ""

# Build Docker image
echo "================================================================================"
echo "Building Frontend Docker Image"
echo "================================================================================"

cd frontend
docker build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL=${BACKEND_URL} \
  -t ${IMAGE_REGISTRY}/frontend:latest .
cd ..

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✓ Frontend image built successfully"
echo ""

# Push to registry
echo "================================================================================"
echo "Pushing to Container Registry"
echo "================================================================================"

docker push ${IMAGE_REGISTRY}/frontend:latest

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed"
    exit 1
fi

echo "✓ Frontend image pushed to registry"
echo ""

# Deploy to Cloud Run
echo "================================================================================"
echo "Deploying to Cloud Run"
echo "================================================================================"

gcloud run deploy buildtrace-frontend \
  --image=${IMAGE_REGISTRY}/frontend:latest \
  --platform=managed \
  --region=${REGION} \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --memory=512Mi --cpu=1 --timeout=300 --max-instances=5 --min-instances=0 \
  --allow-unauthenticated --project=${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

echo "✓ Deployment successful"
echo ""

# Test deployment
echo "================================================================================"
echo "Testing Deployment"
echo "================================================================================"

FRONTEND_URL=$(gcloud run services describe buildtrace-frontend \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format='value(status.url)')

echo "Frontend URL: ${FRONTEND_URL}"

FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" ${FRONTEND_URL})

if [ "$FRONTEND_RESPONSE" = "200" ]; then
    echo "✓ Frontend is accessible"
else
    echo "⚠ Frontend returned: ${FRONTEND_RESPONSE}"
fi

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "Frontend URL: ${FRONTEND_URL}"
echo "Backend URL: ${BACKEND_URL}"
echo ""
echo "Next steps:"
echo "  - Open browser: ${FRONTEND_URL}"
echo "  - Check logs: gcloud run logs read buildtrace-frontend --region=${REGION}"
echo ""
