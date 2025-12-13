# BuildTrace Deployment Guide

This guide explains how to deploy the BuildTrace application (backend + frontend) to Google Cloud Run.

## Quick Start

### Deploy Everything (Backend + Frontend)

```bash
cd buildtrace-dev
./deploy-all.sh
```

This will:
1. Build both backend and frontend Docker images
2. Push images to Google Container Registry
3. Deploy both services to Cloud Run
4. Test both deployments

### Deploy Only Backend

```bash
cd buildtrace-dev
DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh
```

### Deploy Only Frontend

```bash
cd buildtrace-dev
./deploy-frontend.sh
```

or

```bash
DEPLOY_BACKEND=false ./DEPLOY_AND_TEST.sh
```

## Deployment Scripts

### 1. `DEPLOY_AND_TEST.sh` (Main Script)

The comprehensive deployment script with full control.

**Environment Variables:**
- `GCP_PROJECT_ID` - GCP project ID (default: `buildtrace-dev`)
- `GCP_REGION` - GCP region (default: `us-west2`)
- `DEPLOY_BACKEND` - Deploy backend (default: `true`)
- `DEPLOY_FRONTEND` - Deploy frontend (default: `true`)
- `SKIP_LOCAL_TESTS` - Skip local tests (default: `true`)

**Examples:**

```bash
# Deploy both
./DEPLOY_AND_TEST.sh

# Deploy only backend
DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh

# Deploy only frontend
DEPLOY_BACKEND=false ./DEPLOY_AND_TEST.sh

# Deploy to different region
GCP_REGION=us-central1 ./DEPLOY_AND_TEST.sh
```

### 2. `deploy-frontend.sh` (Frontend Only)

Quick script to deploy just the frontend.

```bash
./deploy-frontend.sh
```

This automatically:
- Fetches the backend URL from Cloud Run
- Builds frontend with correct API URL
- Deploys to Cloud Run

### 3. `deploy-all.sh` (Simple Deploy)

Simplest option - just deploys everything.

```bash
./deploy-all.sh
```

## Architecture

### Backend Service

- **Name:** `buildtrace-backend`
- **Image:** `gcr.io/buildtrace-dev/backend:latest`
- **Resources:** 2 CPU, 2Gi memory
- **Timeout:** 3600s (1 hour)
- **Scaling:** Min 1, Max 10 instances
- **URL:** https://buildtrace-backend-136394139608.us-west2.run.app

**Features:**
- Flask REST API
- Cloud SQL (PostgreSQL) integration
- Google Cloud Storage for file uploads
- Pub/Sub for async processing
- Gemini API for AI features
- OpenAI API integration

### Frontend Service

- **Name:** `buildtrace-frontend`
- **Image:** `gcr.io/buildtrace-dev/frontend:latest`
- **Resources:** 1 CPU, 512Mi memory
- **Timeout:** 300s (5 minutes)
- **Scaling:** Min 0, Max 5 instances
- **URL:** https://buildtrace-frontend-136394139608.us-west2.run.app

**Features:**
- Next.js 14 application
- React 18
- TypeScript
- Tailwind CSS
- API integration with backend

### Worker Services (Cloud Run)

All asynchronous processing has been moved off Kubernetes and onto Cloud Run pull subscribers. Each worker reuses the backend codebase and the shared `Dockerfile.worker`.

| Service | Purpose | Deploy Command |
| --- | --- | --- |
| `buildtrace-ocr-worker` | Gemini OCR extraction + page slicing | `gcloud run deploy buildtrace-ocr-worker --image=us-west2-docker.pkg.dev/buildtrace-dev/buildtrace/buildtrace-ocr-worker:latest --region=us-west2` |
| `buildtrace-diff-worker` | Alignment, overlay, and diff metadata generation | `gcloud run deploy buildtrace-diff-worker --image=us-west2-docker.pkg.dev/buildtrace-dev/buildtrace/buildtrace-diff-worker:latest --region=us-west2` |
| `buildtrace-summary-worker` | OpenAI/Gemini summary generation | `gcloud run deploy buildtrace-summary-worker --image=us-west2-docker.pkg.dev/buildtrace-dev/buildtrace/buildtrace-summary-worker:latest --region=us-west2` |

**To build/push an updated worker image:**

```bash
cd buildtrace-dev/backend
docker buildx build \
  --platform linux/amd64 \
  -f Dockerfile.worker \
  -t us-west2-docker.pkg.dev/buildtrace-dev/buildtrace/buildtrace-summary-worker:latest .
docker push us-west2-docker.pkg.dev/buildtrace-dev/buildtrace/buildtrace-summary-worker:latest
gcloud run deploy buildtrace-summary-worker \
  --image=us-west2-docker.pkg.dev/buildtrace-dev/buildtrace/buildtrace-summary-worker:latest \
  --region=us-west2
```

> 💡 **Important:** The workers now scale independently via Cloud Run (min 0, max 10). No Kubernetes cluster is required.

## Configuration

### Backend Environment Variables

Set in Cloud Run:
```
ENVIRONMENT=production
USE_DATABASE=true
USE_GCS=true
USE_PUBSUB=true
GCP_PROJECT_ID=buildtrace-dev
INSTANCE_CONNECTION_NAME=buildtrace-dev:us-west2:buildtrace-dev-db
DB_USER=buildtrace_user
DB_NAME=buildtrace_db
GCS_BUCKET_NAME=buildtrace-dev-input-buildtrace-dev
GCS_UPLOAD_BUCKET=buildtrace-dev-input-buildtrace-dev
GCS_PROCESSED_BUCKET=buildtrace-dev-processed-buildtrace-dev
PUBSUB_OCR_TOPIC=buildtrace-dev-ocr-queue
PUBSUB_DIFF_TOPIC=buildtrace-dev-diff-queue
PUBSUB_SUMMARY_TOPIC=buildtrace-dev-summary-queue
GEMINI_MODEL=models/gemini-2.5-pro
```

### Backend Secrets

Stored in GCP Secret Manager:
- `DB_PASS` - Database password
- `OPENAI_API_KEY` - OpenAI API key
- `SECRET_KEY` - JWT signing key
- `GEMINI_API_KEY` - Gemini API key

### Frontend Environment Variables

Set in Cloud Run:
```
NEXT_PUBLIC_API_URL=https://buildtrace-backend-136394139608.us-west2.run.app
```

This is automatically set during deployment.

## Prerequisites

### Required Tools

- Docker
- gcloud CLI (authenticated)
- bash

### Required GCP Resources

All these should already be set up:

1. **Cloud SQL Instance**
   - Name: `buildtrace-dev-db`
   - Type: PostgreSQL
   - Region: us-west2

2. **Service Account**
   - Name: `buildtrace-service-account@buildtrace-dev.iam.gserviceaccount.com`
   - Permissions: Cloud SQL Client, Storage Admin, Pub/Sub Admin

3. **GCS Buckets**
   - `buildtrace-dev-input-buildtrace-dev`
   - `buildtrace-dev-processed-buildtrace-dev`

4. **Pub/Sub Topics**
   - `buildtrace-dev-ocr-queue`
   - `buildtrace-dev-diff-queue`
   - `buildtrace-dev-summary-queue`

5. **Secrets in Secret Manager**
   - `db-user-password`
   - `openai-api-key`
   - `jwt-signing-key`
   - `gemini-api-key`

## Deployment Process

### What Happens During Deployment

1. **Pre-deployment Checks**
   - Verify directory structure
   - Check Docker and gcloud availability

2. **Build Phase**
   - Backend: Build Python Flask app with all dependencies
   - Frontend: Build Next.js app with backend URL baked in

3. **Push Phase**
   - Push images to Google Container Registry (gcr.io)

4. **Deploy Phase**
   - Backend: Deploy to Cloud Run with all env vars and secrets
   - Frontend: Deploy to Cloud Run with API URL

5. **Test Phase**
   - Backend: Check `/api/v1/health` endpoint
   - Frontend: Check root endpoint

### Typical Deployment Time

- Backend: ~5-8 minutes
- Frontend: ~3-5 minutes
- Total: ~10-15 minutes

## Troubleshooting

### Frontend Not Connecting to Backend

The frontend needs the correct backend URL at build time.

**Solution 1:** Deploy backend first, then frontend
```bash
DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh
./deploy-frontend.sh
```

**Solution 2:** Deploy both together (the script handles this)
```bash
./deploy-all.sh
```

### Build Failures

**Docker Build Failed:**
```bash
# Check Docker daemon
docker ps

# Check disk space
df -h

# Clear Docker cache
docker system prune -a
```

**Push Failed:**
```bash
# Re-authenticate with gcloud
gcloud auth login
gcloud auth configure-docker
```

### Deployment Failures

**Permission Errors:**
```bash
# Check you're using the right project
gcloud config get-value project

# Set correct project
gcloud config set project buildtrace-dev
```

**Secrets Not Found:**
```bash
# List available secrets
gcloud secrets list

# Create missing secret
gcloud secrets create gemini-api-key --data-file=- <<< "YOUR_KEY_HERE"
```

### Service Not Responding

**Check Logs:**
```bash
# Backend logs
gcloud run logs read buildtrace-backend --region=us-west2 --limit=50

# Frontend logs
gcloud run logs read buildtrace-frontend --region=us-west2 --limit=50
```

**Check Service Status:**
```bash
# List all services
gcloud run services list

# Describe specific service
gcloud run services describe buildtrace-backend --region=us-west2
```

## Monitoring

### Check Deployment Status

```bash
gcloud run services list
```

### View Logs

```bash
# Stream backend logs
gcloud run logs tail buildtrace-backend --region=us-west2

# Stream frontend logs
gcloud run logs tail buildtrace-frontend --region=us-west2
```

### Check Service Health

```bash
# Backend health
curl https://buildtrace-backend-136394139608.us-west2.run.app/api/v1/health

# Frontend health
curl https://buildtrace-frontend-136394139608.us-west2.run.app
```

### View Service Details

```bash
# Backend details
gcloud run services describe buildtrace-backend --region=us-west2

# Frontend details
gcloud run services describe buildtrace-frontend --region=us-west2
```

## Rollback

If a deployment fails or introduces issues:

```bash
# List revisions
gcloud run revisions list --service=buildtrace-backend --region=us-west2

# Rollback to specific revision
gcloud run services update-traffic buildtrace-backend \
  --to-revisions=REVISION_NAME=100 \
  --region=us-west2
```

## Cost Optimization

### Current Configuration

- **Backend:** Min 1 instance (always running)
  - Cost: ~$30-50/month base
- **Frontend:** Min 0 instances (scales to zero)
  - Cost: Pay only for actual usage

### To Reduce Costs

```bash
# Scale backend to zero when not in use
gcloud run services update buildtrace-backend \
  --min-instances=0 \
  --region=us-west2

# Restore always-on
gcloud run services update buildtrace-backend \
  --min-instances=1 \
  --region=us-west2
```

## Best Practices

1. **Always deploy backend before frontend** when both are updated
   - Frontend needs backend URL at build time

2. **Test locally before deploying** (optional)
   ```bash
   SKIP_LOCAL_TESTS=false ./DEPLOY_AND_TEST.sh
   ```

3. **Use environment variables** for configuration
   - Don't hardcode URLs or credentials

4. **Monitor logs** after deployment
   - Check for errors or warnings

5. **Use separate scripts** for partial deployments
   - Frontend only: `./deploy-frontend.sh`
   - Backend only: `DEPLOY_FRONTEND=false ./DEPLOY_AND_TEST.sh`

## Support

For issues:
1. Check logs first: `gcloud run logs read <service-name> --region=us-west2`
2. Verify all GCP resources exist
3. Ensure secrets are configured
4. Test locally if possible

## Next Steps After Deployment

1. **Test the Application**
   - Open frontend URL in browser
   - Try uploading a drawing
   - Test API endpoints

2. **Set Up Monitoring**
   - Cloud Run metrics in GCP Console
   - Set up alerts for errors

3. **Configure CI/CD** (Optional)
   - Use Cloud Build for automatic deployments
   - Trigger on git push

4. **Custom Domain** (Optional)
   ```bash
   gcloud run domain-mappings create --service=buildtrace-frontend \
     --domain=yourdomain.com --region=us-west2
   ```
