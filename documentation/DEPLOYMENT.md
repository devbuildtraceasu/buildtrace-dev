# BuildTrace Deployment Guide

Complete guide for deploying BuildTrace to production, including Cloud Run, Docker, and traditional server deployments.

## Table of Contents

1. [Overview](#overview)
2. [Google Cloud Run Deployment](#google-cloud-run-deployment)
3. [Docker Deployment](#docker-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Database Deployment](#database-deployment)
6. [Storage Setup](#storage-setup)
7. [Monitoring & Logging](#monitoring--logging)

## Overview

BuildTrace supports multiple deployment strategies:

1. **Google Cloud Run** (Recommended): Serverless container deployment
2. **Docker Compose**: Local or VM deployment
3. **Traditional Server**: Direct Python deployment

**Production Architecture:**
- **Web App**: Cloud Run (4GB RAM, 2 CPU)
- **Job Processor**: Cloud Run (32GB RAM, 4 CPU)
- **Database**: Cloud SQL PostgreSQL
- **Storage**: Google Cloud Storage

## Google Cloud Run Deployment

### Prerequisites

1. **Google Cloud Project**: Create or select project
2. **Enable APIs**:
```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    storage-component.googleapis.com \
    artifactregistry.googleapis.com \
    cloudtasks.googleapis.com
```

3. **Authenticate**:
```bash
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
gcloud config set project buildtrace
```

### Step 1: Database Setup

See [DATABASE.md](./DATABASE.md) for detailed database setup.

**Quick Setup:**
```bash
# Create Cloud SQL instance
gcloud sql instances create buildtrace-postgres \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --network=default

# Create database
gcloud sql databases create buildtrace_db \
    --instance=buildtrace-postgres

# Create user
gcloud sql users create buildtrace_user \
    --instance=buildtrace-postgres \
    --password=YOUR_SECURE_PASSWORD
```

### Step 2: Storage Setup

```bash
# Create storage bucket
gsutil mb -p buildtrace -c STANDARD -l us-central1 gs://buildtrace-storage

# Set bucket permissions (if needed)
gsutil iam ch allUsers:objectViewer gs://buildtrace-storage

# Set CORS (for direct browser uploads)
cat > cors.json << EOF
[
  {
    "origin": ["*"],
    "method": ["GET", "POST", "PUT"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set cors.json gs://buildtrace-storage
```

### Step 3: Artifact Registry Setup

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create buildtrace-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="BuildTrace Docker images"
```

### Step 4: Deploy Using Cloud Build (Recommended)

**File**: `gcp/deployment/cloudbuild.yaml`

```bash
# Deploy everything
gcloud builds submit --config=gcp/deployment/cloudbuild.yaml .
```

**What This Does:**
1. Builds Docker image
2. Pushes to Artifact Registry
3. Deploys web app to Cloud Run
4. Deploys job processor to Cloud Run
5. Sets environment variables
6. Configures Cloud SQL connection

### Step 5: Manual Deployment

**Build and Push Image:**
```bash
# Build image
docker build -f gcp/deployment/Dockerfile \
    -t us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest
```

**Deploy Web App:**
```bash
gcloud run deploy buildtrace-overlay \
    --image us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --add-cloudsql-instances buildtrace:us-central1:buildtrace-postgres \
    --set-env-vars \
        ENVIRONMENT=production,\
        USE_DATABASE=true,\
        USE_GCS=true,\
        INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres,\
        DB_USER=buildtrace_user,\
        DB_NAME=buildtrace_db,\
        GCS_BUCKET_NAME=buildtrace-storage,\
        OPENAI_API_KEY=sk-...
```

**Deploy Job Processor:**
```bash
gcloud run deploy buildtrace-job-processor \
    --image us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest \
    --region us-central1 \
    --platform managed \
    --no-allow-unauthenticated \
    --memory 32Gi \
    --cpu 4 \
    --timeout 3600 \
    --max-instances 3 \
    --min-instances 1 \
    --add-cloudsql-instances buildtrace:us-central1:buildtrace-postgres \
    --set-env-vars \
        ENVIRONMENT=production,\
        USE_DATABASE=true,\
        USE_GCS=true,\
        INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres,\
        DB_USER=buildtrace_user,\
        DB_NAME=buildtrace_db,\
        GCS_BUCKET_NAME=buildtrace-storage,\
        OPENAI_API_KEY=sk-... \
    --command python,gcp/infrastructure/job_processor.py
```

### Step 6: Initialize Database

```bash
# Connect to Cloud SQL
gcloud sql connect buildtrace-postgres --user=buildtrace_user

# Or use Cloud SQL Proxy
./cloud_sql_proxy -instances=buildtrace:us-central1:buildtrace-postgres=tcp:5432

# Initialize schema
python -c "from gcp.database import init_db; init_db()"
```

### Step 7: Verify Deployment

```bash
# Get service URL
gcloud run services describe buildtrace-overlay --region=us-central1 --format="value(status.url)"

# Test health endpoint
curl https://buildtrace-overlay-[hash]-uc.a.run.app/health

# Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-overlay" --limit=50
```

## Docker Deployment

### Local Docker Compose

**File**: `gcp/deployment/docker-compose.yml`

```bash
cd gcp/deployment
docker-compose up -d
```

**Services:**
- `app`: Web application
- `postgres`: PostgreSQL database
- `job-processor`: Background job processor (optional)

### Custom Docker Deployment

**Build Image:**
```bash
docker build -f gcp/deployment/Dockerfile -t buildtrace:latest .
```

**Run Container:**
```bash
docker run -d \
    --name buildtrace \
    -p 8080:8080 \
    -e ENVIRONMENT=production \
    -e USE_DATABASE=true \
    -e DB_HOST=postgres \
    -e DB_USER=buildtrace_user \
    -e DB_PASS=password \
    -e DB_NAME=buildtrace_db \
    -e OPENAI_API_KEY=sk-... \
    buildtrace:latest
```

## CI/CD Pipeline

### Cloud Build Configuration

**File**: `gcp/deployment/cloudbuild.yaml`

**Pipeline Steps:**
1. Build Docker image
2. Push to Artifact Registry
3. Deploy web app to Cloud Run
4. Deploy job processor to Cloud Run

**Trigger Setup:**
```bash
# Create trigger
gcloud builds triggers create github \
    --name="buildtrace-deploy" \
    --repo-name="buildtrace" \
    --repo-owner="your-org" \
    --branch-pattern="^main$" \
    --build-config="gcp/deployment/cloudbuild.yaml"
```

### GitHub Actions (Alternative)

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - id: 'auth'
        uses: 'google-github-actions/auth@v0'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'
      
      - name: 'Set up Cloud SDK'
        uses: 'google-github-actions/setup-gcloud@v0'
      
      - name: 'Deploy'
        run: |
          gcloud builds submit --config=gcp/deployment/cloudbuild.yaml .
```

## Database Deployment

### Cloud SQL Setup

**Create Instance:**
```bash
gcloud sql instances create buildtrace-postgres \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --backup-start-time=03:00 \
    --enable-bin-log
```

**Create Database:**
```bash
gcloud sql databases create buildtrace_db \
    --instance=buildtrace-postgres
```

**Create User:**
```bash
gcloud sql users create buildtrace_user \
    --instance=buildtrace-postgres \
    --password=YOUR_SECURE_PASSWORD
```

### Database Migrations

**Using Alembic:**
```bash
# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

**Manual Migration:**
```python
from gcp.database import init_db
init_db()
```

### Backup Strategy

**Automated Backups:**
- Cloud SQL automatic backups (enabled by default)
- Daily backups at 3:00 AM
- 7-day retention

**Manual Backup:**
```bash
gcloud sql backups create \
    --instance=buildtrace-postgres \
    --description="Manual backup before migration"
```

**Restore:**
```bash
gcloud sql backups restore BACKUP_ID \
    --backup-instance=buildtrace-postgres \
    --restore-instance=buildtrace-postgres
```

## Storage Setup

### GCS Bucket Configuration

**Create Bucket:**
```bash
gsutil mb -p buildtrace -c STANDARD -l us-central1 gs://buildtrace-storage
```

**Set Lifecycle Policy:**
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
```

```bash
gsutil lifecycle set lifecycle.json gs://buildtrace-storage
```

**Set CORS:**
```json
[
  {
    "origin": ["https://yourdomain.com"],
    "method": ["GET", "POST", "PUT"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

```bash
gsutil cors set cors.json gs://buildtrace-storage
```

## Monitoring & Logging

### Cloud Logging

**View Logs:**
```bash
# Web app logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-overlay" --limit=50

# Job processor logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-job-processor" --limit=50

# All logs
gcloud logging read "resource.type=cloud_run_revision" --limit=100
```

### Cloud Monitoring

**Metrics to Monitor:**
- Request latency
- Request count
- Error rate
- Processing time
- Memory usage
- CPU usage

**Set Up Alerts:**
```bash
# Create alert policy (via Console or API)
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="High Error Rate" \
    --condition-threshold-value=0.05 \
    --condition-threshold-duration=300s
```

### Health Checks

**Endpoint**: `/health`

**Response:**
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "connected",
  "storage": "gcs"
}
```

**Set Up Uptime Check:**
```bash
gcloud monitoring uptime-checks create \
    --display-name="BuildTrace Health Check" \
    --http-check-path="/health" \
    --http-check-port=8080 \
    --period=60s \
    --timeout=10s
```

## Scaling Configuration

### Auto-Scaling

**Web App:**
- Min instances: 0 (scale to zero)
- Max instances: 10
- CPU utilization: 60% (default)

**Job Processor:**
- Min instances: 1 (always warm)
- Max instances: 3
- CPU utilization: 60% (default)

### Manual Scaling

```bash
# Set min instances
gcloud run services update buildtrace-overlay \
    --min-instances=2 \
    --region=us-central1

# Set max instances
gcloud run services update buildtrace-overlay \
    --max-instances=20 \
    --region=us-central1
```

## Security

### IAM Roles

**Service Account Permissions:**
- `roles/cloudsql.client`: Database access
- `roles/storage.objectAdmin`: GCS access
- `roles/cloudtasks.enqueuer`: Cloud Tasks (if using)

**Grant Permissions:**
```bash
gcloud projects add-iam-policy-binding buildtrace \
    --member="serviceAccount:SERVICE_ACCOUNT" \
    --role="roles/cloudsql.client"
```

### Secrets Management

**Store Secrets:**
```bash
# Create secret
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

# Use in Cloud Run
gcloud run services update buildtrace-overlay \
    --update-secrets OPENAI_API_KEY=openai-api-key:latest
```

### Network Security

- **HTTPS Only**: Enforced by Cloud Run
- **Private IP**: Cloud SQL uses private IP
- **VPC**: Can configure VPC connector for private access

## Rollback

### Rollback Deployment

```bash
# List revisions
gcloud run revisions list --service=buildtrace-overlay --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic buildtrace-overlay \
    --to-revisions PREVIOUS_REVISION=100 \
    --region=us-central1
```

### Database Rollback

```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID \
    --backup-instance=buildtrace-postgres \
    --restore-instance=buildtrace-postgres
```

## Troubleshooting

### Common Issues

1. **Deployment Fails**
   - Check Cloud Build logs
   - Verify Dockerfile syntax
   - Check image push permissions

2. **Database Connection Fails**
   - Verify Cloud SQL instance exists
   - Check connection name format
   - Verify service account permissions

3. **Storage Access Fails**
   - Check bucket exists
   - Verify service account has storage permissions
   - Check bucket name in environment variables

4. **High Memory Usage**
   - Increase memory allocation
   - Check for memory leaks
   - Monitor job processor memory

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for more details.

---

**Next Steps**: See [MONITORING.md](./MONITORING.md) for monitoring setup or [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for deployment issues.

