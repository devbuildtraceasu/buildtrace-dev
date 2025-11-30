# Deployment Checklist

## Pre-Deployment Checks

### 1. Code Quality
- [ ] All tests passing
- [ ] No linter errors
- [ ] All imports resolved
- [ ] Dependencies updated in requirements.txt

### 2. Configuration
- [ ] Environment variables set in GCP Secret Manager
- [ ] Database connection configured
- [ ] GCS buckets created and accessible
- [ ] Pub/Sub topics and subscriptions created
- [ ] Service account permissions configured

### 3. New Features (from buildtrace-overlay- migration)
- [ ] Drawing comparison pipeline tested
- [ ] Change analyzer with bounding box guidance tested
- [ ] Complete pipeline tested
- [ ] Local output manager working
- [ ] All outputs saving correctly

## Deployment Steps

### 1. Build Docker Image

```bash
cd buildtrace-dev/backend

# Set variables
export PROJECT_ID="buildtrace-dev"
export REGION="us-west2"
export IMAGE_REGISTRY="gcr.io/${PROJECT_ID}"

# Build backend image
docker build --platform linux/amd64 -t ${IMAGE_REGISTRY}/backend:latest .

# Push to registry
docker push ${IMAGE_REGISTRY}/backend:latest
```

### 2. Deploy to Cloud Run

```bash
# Set instance connection name
export INSTANCE_CONNECTION_NAME="${PROJECT_ID}:${REGION}:buildtrace-dev-db"

# Deploy backend
gcloud run deploy buildtrace-backend \
  --image=${IMAGE_REGISTRY}/backend:latest \
  --platform=managed \
  --region=${REGION} \
  --service-account=buildtrace-service-account@${PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=${INSTANCE_CONNECTION_NAME} \
  --set-env-vars="ENVIRONMENT=production,USE_DATABASE=true,USE_GCS=true,USE_PUBSUB=true,GCP_PROJECT_ID=${PROJECT_ID},INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},DB_USER=buildtrace_user,DB_NAME=buildtrace_db,GCS_BUCKET_NAME=buildtrace-dev-input-buildtrace-dev,GCS_UPLOAD_BUCKET=buildtrace-dev-input-buildtrace-dev,GCS_PROCESSED_BUCKET=buildtrace-dev-processed-buildtrace-dev,PUBSUB_OCR_TOPIC=buildtrace-dev-ocr-queue,PUBSUB_DIFF_TOPIC=buildtrace-dev-diff-queue,PUBSUB_SUMMARY_TOPIC=buildtrace-dev-summary-queue,GEMINI_API_KEY=${GEMINI_API_KEY},GEMINI_MODEL=models/gemini-2.5-pro" \
  --set-secrets="DB_PASS=db-user-password:latest,OPENAI_API_KEY=openai-api-key:latest,SECRET_KEY=jwt-signing-key:latest" \
  --memory=2Gi --cpu=2 --timeout=3600 --max-instances=10 --min-instances=1 \
  --allow-unauthenticated --project=${PROJECT_ID}
```

### 3. Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe buildtrace-backend \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format='value(status.url)')

echo "Service URL: ${SERVICE_URL}"

# Test health endpoint
curl ${SERVICE_URL}/api/v1/health
```

## Post-Deployment Testing

### 1. Local End-to-End Test

```bash
cd buildtrace-dev/backend
python3 test_end_to_end.py
```

### 2. API Endpoint Tests

```bash
# Test health
curl ${SERVICE_URL}/api/v1/health

# Test upload (if authenticated)
curl -X POST ${SERVICE_URL}/api/v1/drawings/upload \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@test.pdf"
```

### 3. Feature-Specific Tests

#### Drawing Comparison
- [ ] Upload old and new PDFs
- [ ] Verify overlay creation
- [ ] Check outputs in GCS/local storage

#### Change Analysis
- [ ] Run change analyzer on overlay
- [ ] Verify spatial location information in results
- [ ] Check JSON outputs saved correctly

#### Chatbot
- [ ] Test chatbot with drawing context
- [ ] Verify multi-turn conversations
- [ ] Check context retrieval working

## Environment Variables

### Required Secrets (GCP Secret Manager)
- `DB_PASS` - Database password
- `OPENAI_API_KEY` - OpenAI API key
- `SECRET_KEY` - JWT signing key
- `GEMINI_API_KEY` - Gemini API key (NEW - for change analyzer)

### Required Environment Variables
- `ENVIRONMENT=production`
- `USE_DATABASE=true`
- `USE_GCS=true`
- `USE_PUBSUB=true`
- `GCP_PROJECT_ID` - GCP project ID
- `INSTANCE_CONNECTION_NAME` - Cloud SQL instance connection
- `DB_USER` - Database user
- `DB_NAME` - Database name
- `GCS_BUCKET_NAME` - GCS bucket for storage
- `GCS_UPLOAD_BUCKET` - GCS bucket for uploads
- `GCS_PROCESSED_BUCKET` - GCS bucket for processed files
- `PUBSUB_OCR_TOPIC` - Pub/Sub topic for OCR jobs
- `PUBSUB_DIFF_TOPIC` - Pub/Sub topic for diff jobs
- `PUBSUB_SUMMARY_TOPIC` - Pub/Sub topic for summary jobs
- `GEMINI_MODEL` - Gemini model name (default: models/gemini-2.5-pro)

## Monitoring

### Cloud Run Metrics
- Request count
- Request latency
- Error rate
- Memory usage
- CPU usage

### Application Logs
- Check Cloud Run logs for errors
- Monitor processing times
- Check for failed jobs

### Storage
- Monitor GCS bucket usage
- Check file uploads
- Verify processed outputs

## Rollback Plan

If deployment fails:

```bash
# List revisions
gcloud run revisions list --service=buildtrace-backend \
  --region=${REGION} \
  --project=${PROJECT_ID}

# Rollback to previous revision
gcloud run services update-traffic buildtrace-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=${REGION} \
  --project=${PROJECT_ID}
```

## New Features in This Deployment

### From buildtrace-overlay- Migration:
1. **Drawing Comparison Pipeline** (`processing/drawing_comparison.py`)
   - PDF to PNG conversion
   - Drawing matching
   - Overlay creation

2. **Change Analyzer** (`processing/change_analyzer.py`)
   - Gemini API integration
   - Enhanced with bounding box guidance
   - Spatial location information

3. **Complete Pipeline** (`processing/complete_pipeline.py`)
   - End-to-end workflow
   - Combines comparison + analysis

4. **Local Output Manager** (`utils/local_output_manager.py`)
   - Enhanced with save_file() and save_json()
   - Session-based organization

## Testing Checklist

- [ ] Upload test drawings
- [ ] Verify OCR processing
- [ ] Test drawing comparison
- [ ] Test change analysis with bounding boxes
- [ ] Test chatbot with context
- [ ] Verify all outputs saved
- [ ] Check logs for errors
- [ ] Verify API endpoints working

## Notes

- All new features support both local dev and GCP production modes
- Outputs are saved locally in dev mode, to GCS in production
- Enhanced change analyzer includes spatial location guidance
- All migrated code uses logging instead of print statements

