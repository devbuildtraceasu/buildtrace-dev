#!/bin/bash
# Complete Deployment and End-to-End Test Script

set -e  # Exit on error

echo "================================================================================"
echo "BUILTRACE DEPLOYMENT AND END-TO-END TEST"
echo "================================================================================"
echo ""

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-buildtrace-dev}"
REGION="${GCP_REGION:-us-west2}"
IMAGE_REGISTRY="gcr.io/${PROJECT_ID}"
INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME:-${PROJECT_ID}:${REGION}:buildtrace-dev-db}"
SKIP_LOCAL_TESTS="${SKIP_LOCAL_TESTS:-true}"  # Set to "false" to enable local tests
DEPLOY_BACKEND="${DEPLOY_BACKEND:-true}"  # Set to "false" to skip backend
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-true}"  # Set to "false" to skip frontend

echo "Configuration:"
echo "  Project ID: ${PROJECT_ID}"
echo "  Region: ${REGION}"
echo "  Image Registry: ${IMAGE_REGISTRY}"
echo "  Instance: ${INSTANCE_CONNECTION_NAME}"
echo "  Deploy Backend: ${DEPLOY_BACKEND}"
echo "  Deploy Frontend: ${DEPLOY_FRONTEND}"
echo ""

# Step 1: Pre-deployment checks
echo "================================================================================"
echo "STEP 1: Pre-Deployment Checks"
echo "================================================================================"

# Check if we're in the right directory
if [ ! -f "backend/app.py" ] || [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: Must run from buildtrace-dev directory"
    exit 1
fi

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }
command -v gcloud >/dev/null 2>&1 || { echo "❌ gcloud not found"; exit 1; }

echo "✓ Pre-deployment checks passed"
echo ""

# Step 2: Run local end-to-end test (optional)
if [ "$SKIP_LOCAL_TESTS" != "true" ]; then
    echo "================================================================================"
    echo "STEP 2: Local End-to-End Test"
    echo "================================================================================"

    cd backend
    python3 test_e2e_complete.py

    if [ $? -ne 0 ]; then
        echo "❌ Local tests failed. Fix issues before deploying."
        exit 1
    fi

    echo "✓ Local tests passed"
    echo ""
    cd ..
else
    echo "================================================================================"
    echo "STEP 2: Local End-to-End Test (SKIPPED)"
    echo "================================================================================"
    echo "⚠ Local tests disabled. Set SKIP_LOCAL_TESTS=false to enable."
    echo ""
fi

# Step 3: Build Docker Images
echo "================================================================================"
echo "STEP 3: Building Docker Images"
echo "================================================================================"

if [ "$DEPLOY_BACKEND" = "true" ]; then
    echo "Building backend image..."
    cd backend
    docker build --platform linux/amd64 -t ${IMAGE_REGISTRY}/backend:latest .
    cd ..

    if [ $? -ne 0 ]; then
        echo "❌ Backend Docker build failed"
        exit 1
    fi
    echo "✓ Backend image built successfully"
else
    echo "⚠ Skipping backend build"
fi

if [ "$DEPLOY_FRONTEND" = "true" ]; then
    echo "Building frontend image..."
    # Get backend URL for build-time configuration
    BACKEND_URL=$(gcloud run services describe buildtrace-backend \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --format='value(status.url)' 2>/dev/null || echo "https://buildtrace-backend-136394139608.us-west2.run.app")

    cd frontend
    docker build --platform linux/amd64 \
      --build-arg NEXT_PUBLIC_API_URL=${BACKEND_URL} \
      -t ${IMAGE_REGISTRY}/frontend:latest .
    cd ..

    if [ $? -ne 0 ]; then
        echo "❌ Frontend Docker build failed"
        exit 1
    fi
    echo "✓ Frontend image built successfully"
else
    echo "⚠ Skipping frontend build"
fi

echo ""

# Step 4: Push to Container Registry
echo "================================================================================"
echo "STEP 4: Pushing to Container Registry"
echo "================================================================================"

if [ "$DEPLOY_BACKEND" = "true" ]; then
    echo "Pushing backend image to ${IMAGE_REGISTRY}..."
    docker push ${IMAGE_REGISTRY}/backend:latest

    if [ $? -ne 0 ]; then
        echo "❌ Backend Docker push failed"
        exit 1
    fi
    echo "✓ Backend image pushed to registry"
else
    echo "⚠ Skipping backend push"
fi

if [ "$DEPLOY_FRONTEND" = "true" ]; then
    echo "Pushing frontend image to ${IMAGE_REGISTRY}..."
    docker push ${IMAGE_REGISTRY}/frontend:latest

    if [ $? -ne 0 ]; then
        echo "❌ Frontend Docker push failed"
        exit 1
    fi
    echo "✓ Frontend image pushed to registry"
else
    echo "⚠ Skipping frontend push"
fi

echo ""

# Step 5: Deploy to Cloud Run
echo "================================================================================"
echo "STEP 5: Deploying to Cloud Run"
echo "================================================================================"

if [ "$DEPLOY_BACKEND" = "true" ]; then
    # Get URLs for OAuth configuration
    BACKEND_URL=$(gcloud run services describe buildtrace-backend \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --format='value(status.url)' 2>/dev/null || echo "https://buildtrace-backend-136394139608.us-west2.run.app")

    FRONTEND_URL=$(gcloud run services describe buildtrace-frontend \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --format='value(status.url)' 2>/dev/null || echo "https://buildtrace-frontend-136394139608.us-west2.run.app")

    echo "Deploying buildtrace-backend..."
    echo "  Backend URL: ${BACKEND_URL}"
    echo "  Frontend URL: ${FRONTEND_URL}"
    echo "  OAuth Redirect: ${BACKEND_URL}/api/v1/auth/google/callback"

    gcloud run deploy buildtrace-backend \
      --image=${IMAGE_REGISTRY}/backend:latest \
      --platform=managed \
      --region=${REGION} \
      --service-account=buildtrace-service-account@${PROJECT_ID}.iam.gserviceaccount.com \
      --add-cloudsql-instances=${INSTANCE_CONNECTION_NAME} \
      --set-env-vars="ENVIRONMENT=production,USE_DATABASE=true,USE_GCS=true,USE_PUBSUB=false,GCP_PROJECT_ID=${PROJECT_ID},INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},DB_USER=buildtrace_user,DB_NAME=buildtrace_db,GCS_BUCKET_NAME=buildtrace-dev-input-buildtrace-dev,GCS_UPLOAD_BUCKET=buildtrace-dev-input-buildtrace-dev,GCS_PROCESSED_BUCKET=buildtrace-dev-processed-buildtrace-dev,PUBSUB_OCR_TOPIC=buildtrace-dev-ocr-queue,PUBSUB_DIFF_TOPIC=buildtrace-dev-diff-queue,PUBSUB_SUMMARY_TOPIC=buildtrace-dev-summary-queue,GEMINI_MODEL=models/gemini-2.5-pro,GOOGLE_REDIRECT_URI=${BACKEND_URL}/api/v1/auth/google/callback,FRONTEND_URL=${FRONTEND_URL}" \
      --set-secrets="DB_PASS=db-user-password:latest,OPENAI_API_KEY=openai-api-key:latest,SECRET_KEY=jwt-signing-key:latest,GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest" \
      --memory=2Gi --cpu=2 --timeout=3600 --max-instances=10 --min-instances=1 \
      --allow-unauthenticated --project=${PROJECT_ID}

    if [ $? -ne 0 ]; then
        echo "❌ Backend deployment failed"
        exit 1
    fi
    echo "✓ Backend deployment successful"
else
    echo "⚠ Skipping backend deployment"
fi

if [ "$DEPLOY_FRONTEND" = "true" ]; then
    # Get the backend URL for runtime configuration
    BACKEND_URL=$(gcloud run services describe buildtrace-backend \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --format='value(status.url)')

    echo "Deploying buildtrace-frontend..."
    gcloud run deploy buildtrace-frontend \
      --image=${IMAGE_REGISTRY}/frontend:latest \
      --platform=managed \
      --region=${REGION} \
      --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
      --memory=512Mi --cpu=1 --timeout=300 --max-instances=5 --min-instances=0 \
      --allow-unauthenticated --project=${PROJECT_ID}

    if [ $? -ne 0 ]; then
        echo "❌ Frontend deployment failed"
        exit 1
    fi
    echo "✓ Frontend deployment successful"
else
    echo "⚠ Skipping frontend deployment"
fi

echo ""

# Step 6: Get service URLs and test
echo "================================================================================"
echo "STEP 6: Testing Deployed Services"
echo "================================================================================"

if [ "$DEPLOY_BACKEND" = "true" ]; then
    BACKEND_URL=$(gcloud run services describe buildtrace-backend \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --format='value(status.url)')

    echo "Backend URL: ${BACKEND_URL}"

    # Test health endpoint
    echo "Testing backend health endpoint..."
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" ${BACKEND_URL}/api/v1/health)

    if [ "$HEALTH_RESPONSE" = "200" ]; then
        echo "✓ Backend health check passed"
    else
        echo "⚠ Backend health check returned: ${HEALTH_RESPONSE}"
    fi
fi

if [ "$DEPLOY_FRONTEND" = "true" ]; then
    FRONTEND_URL=$(gcloud run services describe buildtrace-frontend \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --format='value(status.url)')

    echo "Frontend URL: ${FRONTEND_URL}"

    # Test frontend endpoint
    echo "Testing frontend..."
    FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" ${FRONTEND_URL})

    if [ "$FRONTEND_RESPONSE" = "200" ]; then
        echo "✓ Frontend is accessible"
    else
        echo "⚠ Frontend returned: ${FRONTEND_RESPONSE}"
    fi
fi

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""

if [ "$DEPLOY_BACKEND" = "true" ]; then
    echo "Backend URL: ${BACKEND_URL}"
fi

if [ "$DEPLOY_FRONTEND" = "true" ]; then
    echo "Frontend URL: ${FRONTEND_URL}"
fi

echo ""
echo "Next steps:"
if [ "$DEPLOY_BACKEND" = "true" ]; then
    echo "  Backend:"
    echo "    - Test API: curl ${BACKEND_URL}/api/v1/health"
    echo "    - Check logs: gcloud run logs read buildtrace-backend --region=${REGION}"
fi
if [ "$DEPLOY_FRONTEND" = "true" ]; then
    echo "  Frontend:"
    echo "    - Open browser: ${FRONTEND_URL}"
    echo "    - Check logs: gcloud run logs read buildtrace-frontend --region=${REGION}"
fi
echo ""
