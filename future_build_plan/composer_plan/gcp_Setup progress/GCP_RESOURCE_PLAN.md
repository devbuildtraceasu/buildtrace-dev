# BuildTrace System - Comprehensive GCP Resource Plan

_Last updated: 2025-01-XX_

This document provides a comprehensive, detailed plan for all GCP resources required for the BuildTrace system across three phases:
1. **Before Development** - Infrastructure setup and prerequisites
2. **During Development** - Development, testing, and CI/CD resources
3. **After Development** - Production monitoring, alerting, and maintenance

This plan is designed to be implementation-ready with step-by-step instructions, similar to the detailed implementation guides.

---

## Table of Contents

1. [Phase 1: Before Development - Infrastructure Setup](#phase-1-before-development---infrastructure-setup)
2. [Phase 2: During Development - Development Resources](#phase-2-during-development---development-resources)
3. [Phase 3: After Development - Production & Monitoring](#phase-3-after-development---production--monitoring)
4. [Quick Reference Commands](#quick-reference-commands)
5. [Cost Estimation](#cost-estimation)
6. [Security Checklist](#security-checklist)

---

## Phase 1: Before Development - Infrastructure Setup

### 1.1 GCP Project Setup

#### Task: Create or Select GCP Project

**Steps:**
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "NEW PROJECT" or select existing project
4. Enter project name: `buildtrace-prod` (or `buildtrace-dev` for development)
5. Note the Project ID (e.g., `buildtrace-prod-123456`)
6. Click "CREATE"

**Enable Billing:**
1. Go to "Billing" in the left navigation menu
2. Click "LINK A BILLING ACCOUNT"
3. Select or create a billing account
4. Ensure billing is enabled for the project

**Set IAM Permissions:**
1. Go to "IAM & Admin" > "IAM"
2. Ensure your user has:
   - Owner role (for full access) OR
   - Editor + Security Admin + Service Usage Admin roles (minimum)
3. For team members, grant appropriate roles:
   - Developers: Editor + Cloud Run Admin + Cloud Build Editor
   - DevOps: Editor + Kubernetes Engine Admin + Monitoring Admin
   - Read-only: Viewer + Monitoring Viewer

**Store Project Information:**
```bash
# Set these as environment variables
export PROJECT_ID="buildtrace-prod-123456"
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export REGION="us-west2"  # Choose your preferred region
export ZONE="us-west2-a"   # For zonal resources

# Save to .env file for reuse
cat > .env << EOF
PROJECT_ID=$PROJECT_ID
PROJECT_NUMBER=$PROJECT_NUMBER
REGION=$REGION
ZONE=$ZONE
EOF
```

**Project Organization:**
```bash
# Create separate projects for different environments
# Development
gcloud projects create buildtrace-dev --name="BuildTrace Development"

# Staging
gcloud projects create buildtrace-staging --name="BuildTrace Staging"

# Production
gcloud projects create buildtrace-prod --name="BuildTrace Production"
```

---

### 1.2 Enable Required GCP APIs

#### Task: Enable All Required APIs

**Required APIs for BuildTrace:**

**Core Services:**
- Cloud Run Admin API (`run.googleapis.com`) - For serverless containers
- Google Kubernetes Engine API (`container.googleapis.com`) - For GKE cluster
- Cloud Build API (`cloudbuild.googleapis.com`) - For CI/CD
- Artifact Registry API (`artifactregistry.googleapis.com`) - For Docker images

**Messaging & Queuing:**
- Cloud Pub/Sub API (`pubsub.googleapis.com`) - For job queues
- Cloud Tasks API (`cloudtasks.googleapis.com`) - Alternative queue system

**Storage & Database:**
- Cloud Storage API (`storage-component.googleapis.com`) - For object storage
- Cloud SQL Admin API (`sqladmin.googleapis.com`) - For managed PostgreSQL
- BigQuery API (`bigquery.googleapis.com`) - For analytics (optional)

**Monitoring & Logging:**
- Cloud Logging API (`logging.googleapis.com`) - For application logs
- Cloud Monitoring API (`monitoring.googleapis.com`) - For metrics
- Error Reporting API (`clouderrorreporting.googleapis.com`) - For error tracking

**Networking:**
- Compute Engine API (`compute.googleapis.com`) - For GKE nodes
- Cloud Resource Manager API (`cloudresourcemanager.googleapis.com`) - For resource management

**Security:**
- Secret Manager API (`secretmanager.googleapis.com`) - For secrets
- Cloud IAM API (`iam.googleapis.com`) - For access control

**Via gcloud CLI (Recommended):**
```bash
# Set project
gcloud config set project $PROJECT_ID

# Enable all APIs at once
gcloud services enable \
  run.googleapis.com \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  cloudtasks.googleapis.com \
  storage-component.googleapis.com \
  sqladmin.googleapis.com \
  bigquery.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  clouderrorreporting.googleapis.com \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled --format="table(serviceName,config.name)"

# Check for any failed enables
gcloud services list --enabled --filter="state:ENABLED"
```

**Expected Output:**
- All APIs should show status "ENABLED"
- This may take 2-5 minutes
- Some APIs may require additional permissions

**Via GCP Console:**
1. Navigate to "APIs & Services" > "Library"
2. Search for each API name
3. Click on the API
4. Click "ENABLE"
5. Repeat for all APIs

**API Quotas & Limits:**
```bash
# Check current quotas
gcloud compute project-info describe --project=$PROJECT_ID

# Request quota increases if needed
# Go to: IAM & Admin > Quotas
# Search for specific quotas (e.g., "Cloud Run instances")
# Click "EDIT QUOTAS" and request increase
```

---

### 1.3 Cloud Storage Setup

#### Task: Create Storage Buckets

**Step 1: Create Input Bucket**
```bash
# Create bucket for input files (PDFs, DWG, images)
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-prod-input-$PROJECT_ID

# Or via console:
# 1. Navigate to "Cloud Storage" > "Buckets"
# 2. Click "CREATE BUCKET"
# 3. Name: buildtrace-prod-input-{project-id}
# 4. Location type: Region
# 5. Region: us-west2 (or your chosen region)
# 6. Storage class: Standard
# 7. Access control: Uniform
# 8. Click "CREATE"
```

**Step 2: Create Processed Data Bucket**
```bash
# Create bucket for processed data (OCR results, diff JSONs)
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-prod-processed-$PROJECT_ID
```

**Step 3: Create Artifacts Bucket**
```bash
# Create bucket for artifacts (overlays, summaries, exports)
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-prod-artifacts-$PROJECT_ID
```

**Step 4: Create Logs Bucket (Optional)**
```bash
# Create bucket for log exports
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-prod-logs-$PROJECT_ID
```

**Step 5: Create Folder Structure**
```bash
# Input bucket structure
gsutil mkdir gs://buildtrace-prod-input-$PROJECT_ID/raw/
gsutil mkdir gs://buildtrace-prod-input-$PROJECT_ID/uploaded/
gsutil mkdir gs://buildtrace-prod-input-$PROJECT_ID/failed/

# Processed bucket structure
gsutil mkdir gs://buildtrace-prod-processed-$PROJECT_ID/ocr/
gsutil mkdir gs://buildtrace-prod-processed-$PROJECT_ID/diffs/
gsutil mkdir gs://buildtrace-prod-processed-$PROJECT_ID/rasterized/

# Artifacts bucket structure
gsutil mkdir gs://buildtrace-prod-artifacts-$PROJECT_ID/overlays/
gsutil mkdir gs://buildtrace-prod-artifacts-$PROJECT_ID/overlays/machine/
gsutil mkdir gs://buildtrace-prod-artifacts-$PROJECT_ID/overlays/manual/
gsutil mkdir gs://buildtrace-prod-artifacts-$PROJECT_ID/summaries/
gsutil mkdir gs://buildtrace-prod-artifacts-$PROJECT_ID/exports/
```

**Step 6: Set Bucket Permissions**
```bash
# Remove public access (make buckets private)
gsutil iam ch -d allUsers:objectViewer gs://buildtrace-prod-input-$PROJECT_ID
gsutil iam ch -d allUsers:objectViewer gs://buildtrace-prod-processed-$PROJECT_ID
gsutil iam ch -d allUsers:objectViewer gs://buildtrace-prod-artifacts-$PROJECT_ID

# Grant service account access (we'll do this after creating service account)
# gsutil iam ch serviceAccount:buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://buildtrace-prod-input-$PROJECT_ID
# gsutil iam ch serviceAccount:buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://buildtrace-prod-processed-$PROJECT_ID
# gsutil iam ch serviceAccount:buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://buildtrace-prod-artifacts-$PROJECT_ID
```

**Step 7: Configure Lifecycle Policies**
```bash
# Create lifecycle policy file (lifecycle.json)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365}
      }
    ]
  }
}
EOF

# Apply lifecycle policy to input bucket
gsutil lifecycle set lifecycle.json gs://buildtrace-prod-input-$PROJECT_ID

# Create separate policy for processed data (keep longer)
cat > lifecycle-processed.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 60}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 180}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 730}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle-processed.json gs://buildtrace-prod-processed-$PROJECT_ID
```

**Step 8: Enable Versioning (Optional)**
```bash
# Enable versioning for critical buckets
gsutil versioning set on gs://buildtrace-prod-artifacts-$PROJECT_ID
```

**Step 9: Configure CORS (if needed for direct browser uploads)**
```bash
# Create CORS configuration
cat > cors.json << EOF
[
  {
    "origin": ["https://app.buildtrace.ai", "https://*.buildtrace.ai"],
    "method": ["GET", "POST", "PUT", "DELETE", "HEAD"],
    "responseHeader": ["Content-Type", "Authorization"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Apply CORS configuration
gsutil cors set cors.json gs://buildtrace-prod-input-$PROJECT_ID
```

---

### 1.4 Database Setup

#### Option A: Cloud SQL (PostgreSQL) - Recommended

**Step 1: Create Cloud SQL Instance**

**Via Console:**
1. Navigate to "SQL" > "Create Instance"
2. Choose "PostgreSQL"
3. Instance ID: `buildtrace-prod-db`
4. Root password: Set a strong password (save it securely in Secret Manager!)
5. Region: Same as your project region
6. Database version: PostgreSQL 15 (or latest)
7. Machine type: 
   - Development: `db-f1-micro` (shared-core, 0.6 GB RAM)
   - Staging: `db-n1-standard-1` (1 vCPU, 3.75 GB RAM)
   - Production: `db-n1-standard-4` (4 vCPU, 15 GB RAM) or higher
8. Storage: 
   - Development: 10 GB SSD
   - Production: 100 GB SSD (with autoscaling)
9. Enable backups: Yes
10. Backup window: Configure off-peak hours
11. Enable point-in-time recovery: Yes (for production)
12. Click "CREATE"

**Via gcloud CLI:**
```bash
# Create Cloud SQL instance
gcloud sql instances create buildtrace-prod-db \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-4 \
  --region=$REGION \
  --root-password=$(openssl rand -base64 32) \
  --storage-type=SSD \
  --storage-size=100GB \
  --storage-auto-increase \
  --backup-start-time=02:00 \
  --enable-bin-log \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=3 \
  --deletion-protection

# Store password in Secret Manager
echo -n "YOUR_PASSWORD" | gcloud secrets create db-root-password \
  --data-file=- \
  --replication-policy="automatic"

# Get connection name
export DB_CONNECTION_NAME=$(gcloud sql instances describe buildtrace-prod-db \
  --format="value(connectionName)")
echo "Connection name: $DB_CONNECTION_NAME"
```

**Step 2: Create Database**
```bash
# Create database
gcloud sql databases create buildtrace_db --instance=buildtrace-prod-db

# Create database user
gcloud sql users create buildtrace_user \
  --instance=buildtrace-prod-db \
  --password=$(openssl rand -base64 32)

# Store user password in Secret Manager
echo -n "USER_PASSWORD" | gcloud secrets create db-user-password \
  --data-file=- \
  --replication-policy="automatic"
```

**Step 3: Configure Network Access**
```bash
# Allow access from GKE cluster (private IP)
# This is done automatically when connecting via Cloud SQL Proxy

# For local development, add your IP
gcloud sql instances patch buildtrace-prod-db \
  --authorized-networks=$(curl -s https://api.ipify.org)/32

# Or allow all IPs (NOT RECOMMENDED for production)
# gcloud sql instances patch buildtrace-prod-db --authorized-networks=0.0.0.0/0
```

**Step 4: Create Database Schema**
```bash
# Connect to database and create schema
# Using Cloud SQL Proxy (recommended)
cloud_sql_proxy -instances=$DB_CONNECTION_NAME=tcp:5432 &

# Or using gcloud
gcloud sql connect buildtrace-prod-db --user=buildtrace_user --database=buildtrace_db

# Then run schema.sql (see architecture2.md for schema)
psql "host=/cloudsql/$DB_CONNECTION_NAME dbname=buildtrace_db user=buildtrace_user" < schema.sql
```

**Step 5: Configure Read Replicas (Production)**
```bash
# Create read replica for production
gcloud sql instances create buildtrace-prod-db-replica \
  --master-instance-name=buildtrace-prod-db \
  --region=$REGION \
  --tier=db-n1-standard-2
```

#### Option B: BigQuery (For Analytics)

**Step 1: Create BigQuery Dataset**
```bash
# Create dataset
bq mk --dataset --location=$REGION buildtrace_analytics

# Or via console:
# 1. Navigate to "BigQuery" > "Datasets"
# 2. Click "CREATE DATASET"
# 3. Dataset ID: buildtrace_analytics
# 4. Location: us-west2
# 5. Click "CREATE"
```

**Step 2: Create Tables for Metrics**
```bash
# Create processing_metrics table
bq mk --table buildtrace_analytics.processing_metrics \
  job_id:STRING,drawing_id:STRING,stage:STRING,latency_ms:INTEGER,status:STRING,created_at:TIMESTAMP

# Create job_metrics table
bq mk --table buildtrace_analytics.job_metrics \
  job_id:STRING,project_id:STRING,status:STRING,duration_seconds:INTEGER,created_at:TIMESTAMP

# Create error_metrics table
bq mk --table buildtrace_analytics.error_metrics \
  error_id:STRING,job_id:STRING,error_type:STRING,error_message:STRING,created_at:TIMESTAMP
```

---

### 1.5 Pub/Sub Setup

#### Task: Create Pub/Sub Topics and Subscriptions

**Step 1: Create Main Topics**
```bash
# Create OCR queue topic
gcloud pubsub topics create buildtrace-prod-ocr-queue

# Create Diff queue topic
gcloud pubsub topics create buildtrace-prod-diff-queue

# Create Summary queue topic
gcloud pubsub topics create buildtrace-prod-summary-queue

# Create Orchestrator queue topic (internal)
gcloud pubsub topics create buildtrace-prod-orchestrator-queue

# Or via console:
# 1. Navigate to "Pub/Sub" > "Topics"
# 2. Click "CREATE TOPIC"
# 3. Topic ID: buildtrace-prod-ocr-queue
# 4. Click "CREATE"
# 5. Repeat for all topics
```

**Step 2: Create Dead-Letter Topics**
```bash
# Create DLQ for each main topic
gcloud pubsub topics create buildtrace-prod-ocr-dlq
gcloud pubsub topics create buildtrace-prod-diff-dlq
gcloud pubsub topics create buildtrace-prod-summary-dlq
```

**Step 3: Create Push Subscriptions**
```bash
# First, get your Cloud Run service URLs (after deploying workers)
# For now, we'll create pull subscriptions and convert later

# Create OCR worker subscription
gcloud pubsub subscriptions create buildtrace-prod-ocr-worker-sub \
  --topic=buildtrace-prod-ocr-queue \
  --ack-deadline=600 \
  --dead-letter-topic=buildtrace-prod-ocr-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d

# Create Diff worker subscription
gcloud pubsub subscriptions create buildtrace-prod-diff-worker-sub \
  --topic=buildtrace-prod-diff-queue \
  --ack-deadline=600 \
  --dead-letter-topic=buildtrace-prod-diff-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d

# Create Summary worker subscription
gcloud pubsub subscriptions create buildtrace-prod-summary-worker-sub \
  --topic=buildtrace-prod-summary-queue \
  --ack-deadline=600 \
  --dead-letter-topic=buildtrace-prod-summary-dlq \
  --max-delivery-attempts=5 \
  --message-retention-duration=7d

# Note: We'll update these to push subscriptions after deploying workers
```

**Step 4: Create Dead-Letter Subscriptions**
```bash
# Create subscriptions for DLQ topics (for monitoring)
gcloud pubsub subscriptions create buildtrace-prod-ocr-dlq-sub \
  --topic=buildtrace-prod-ocr-dlq

gcloud pubsub subscriptions create buildtrace-prod-diff-dlq-sub \
  --topic=buildtrace-prod-diff-dlq

gcloud pubsub subscriptions create buildtrace-prod-summary-dlq-sub \
  --topic=buildtrace-prod-summary-dlq
```

**Step 5: Configure Subscription Settings**
```bash
# Update subscription with expiration (optional)
gcloud pubsub subscriptions update buildtrace-prod-ocr-worker-sub \
  --expiration-period=never

# Set message ordering (if needed)
gcloud pubsub subscriptions update buildtrace-prod-ocr-worker-sub \
  --enable-message-ordering
```

---

### 1.6 GKE Cluster Setup (If Using Kubernetes)

#### Task: Create GKE Cluster

**Step 1: Create GKE Cluster**

**Via Console:**
1. Navigate to "Kubernetes Engine" > "Clusters"
2. Click "CREATE CLUSTER"
3. Choose "GKE Standard" (not Autopilot for more control)
4. Configure:
   - Name: `buildtrace-prod-cluster`
   - Location type: Regional
   - Region: `us-west2`
   - Kubernetes version: Latest stable
   - Release channel: Regular (or Rapid for latest features)
5. Node pool configuration:
   - Name: `web-standard-pool`
   - Machine type: `e2-standard-4` (4 vCPU, 16 GB RAM)
   - Number of nodes: 3 (minimum for high availability)
   - Enable autoscaling: Yes (min: 3, max: 10)
6. Security:
   - Enable Workload Identity: Yes
   - Enable Network Policy: Yes
   - Enable Binary Authorization: Yes (optional)
7. Networking:
   - VPC: default (or create custom VPC)
   - Enable private cluster: Yes (recommended)
   - Enable authorized networks: Configure your IPs
8. Click "CREATE"

**Via gcloud CLI:**
```bash
# Create GKE cluster
gcloud container clusters create buildtrace-prod-cluster \
  --region=$REGION \
  --num-nodes=3 \
  --min-nodes=3 \
  --max-nodes=10 \
  --machine-type=e2-standard-4 \
  --enable-autoscaling \
  --enable-autorepair \
  --enable-autoupgrade \
  --release-channel=regular \
  --workload-pool=$PROJECT_ID.svc.id.goog \
  --enable-network-policy \
  --enable-private-nodes \
  --master-authorized-networks=$(curl -s https://api.ipify.org)/32 \
  --addons=HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver

# Get cluster credentials
gcloud container clusters get-credentials buildtrace-prod-cluster --region=$REGION

# Verify cluster
kubectl get nodes
```

**Step 2: Create Additional Node Pools**
```bash
# Create worker node pool (for CPU-intensive tasks)
gcloud container node-pools create workers-cpu-pool \
  --cluster=buildtrace-prod-cluster \
  --region=$REGION \
  --num-nodes=2 \
  --min-nodes=2 \
  --max-nodes=20 \
  --machine-type=e2-standard-8 \
  --enable-autoscaling \
  --node-taints=workload=workers:NoSchedule \
  --node-labels=workload=workers

# Create GPU node pool (optional, for future ML workloads)
# gcloud container node-pools create workers-gpu-pool \
#   --cluster=buildtrace-prod-cluster \
#   --region=$REGION \
#   --num-nodes=0 \
#   --min-nodes=0 \
#   --max-nodes=5 \
#   --machine-type=n1-standard-4 \
#   --accelerator=type=nvidia-tesla-t4,count=1 \
#   --enable-autoscaling
```

**Step 3: Configure Namespaces**
```bash
# Create namespaces
kubectl create namespace prod-app
kubectl create namespace prod-observability
kubectl create namespace prod-infra

# Label namespaces
kubectl label namespace prod-app environment=production
kubectl label namespace prod-observability environment=production
```

---

### 1.7 Service Account Setup

#### Task: Create and Configure Service Accounts

**Step 1: Create Service Accounts**
```bash
# Create main service account for application
gcloud iam service-accounts create buildtrace-service-account \
  --display-name="BuildTrace Service Account" \
  --description="Service account for BuildTrace application services"

# Create service account for Cloud Build
gcloud iam service-accounts create buildtrace-cloudbuild \
  --display-name="BuildTrace Cloud Build" \
  --description="Service account for Cloud Build CI/CD"

# Create service account for GKE workloads
gcloud iam service-accounts create buildtrace-gke-workload \
  --display-name="BuildTrace GKE Workload" \
  --description="Service account for GKE workloads"

# Get service account emails
export SERVICE_ACCOUNT_EMAIL="buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com"
export CLOUDBUILD_SA="buildtrace-cloudbuild@$PROJECT_ID.iam.gserviceaccount.com"
export GKE_WORKLOAD_SA="buildtrace-gke-workload@$PROJECT_ID.iam.gserviceaccount.com"
```

**Step 2: Grant Required Roles to Application Service Account**
```bash
# Cloud Run permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.invoker"

# Storage permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"

# Pub/Sub permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/pubsub.publisher"

# Cloud SQL permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"

# Logging permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/logging.logWriter"

# Monitoring permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/monitoring.metricWriter"

# Secret Manager permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

**Step 3: Grant Roles to Cloud Build Service Account**
```bash
# Cloud Build permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/cloudbuild.builds.editor"

# Artifact Registry permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/artifactregistry.writer"

# Cloud Run permissions (to deploy)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/run.admin"

# GKE permissions (if deploying to GKE)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/container.developer"

# Service Account User (to impersonate)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/iam.serviceAccountUser"
```

**Step 4: Grant Roles to GKE Workload Service Account**
```bash
# Storage permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/storage.objectAdmin"

# Pub/Sub permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/pubsub.publisher"

# Cloud SQL permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/cloudsql.client"

# Logging and Monitoring
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/monitoring.metricWriter"

# Secret Manager
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/secretmanager.secretAccessor"
```

**Step 5: Configure Workload Identity (for GKE)**
```bash
# Bind Kubernetes service account to GCP service account
gcloud iam service-accounts add-iam-policy-binding $GKE_WORKLOAD_SA \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[prod-app/buildtrace-workload]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount buildtrace-workload \
  -n prod-app \
  iam.gke.io/gcp-service-account=$GKE_WORKLOAD_SA
```

**Step 6: Generate Service Account Key (for local testing)**
```bash
# Create key file
gcloud iam service-accounts keys create buildtrace-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

# Set environment variable for local use
export GOOGLE_APPLICATION_CREDENTIALS="./buildtrace-key.json"

# Add to .gitignore (IMPORTANT!)
echo "buildtrace-key.json" >> .gitignore
echo "*.json" >> .gitignore  # Be careful with this
```

---

### 1.8 Artifact Registry Setup

#### Task: Create Docker Repository

**Step 1: Create Repository**
```bash
# Create Artifact Registry repository
gcloud artifacts repositories create buildtrace-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for BuildTrace"

# Or via console:
# 1. Navigate to "Artifact Registry" > "Repositories"
# 2. Click "CREATE REPOSITORY"
# 3. Name: buildtrace-repo
# 4. Format: Docker
# 5. Mode: Standard
# 6. Location: us-west2
# 7. Click "CREATE"
```

**Step 2: Configure Docker Authentication**
```bash
# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker $REGION-docker.pkg.dev

# Or manually:
gcloud auth print-access-token | docker login -u oauth2accesstoken --password-stdin $REGION-docker.pkg.dev
```

**Step 3: Grant Cloud Build Permissions**
```bash
# Grant Cloud Build service account access
gcloud artifacts repositories add-iam-policy-binding buildtrace-repo \
  --location=$REGION \
  --member="serviceAccount:$CLOUDBUILD_SA" \
  --role="roles/artifactregistry.writer"

# Also grant to default Cloud Build service account
export DEFAULT_CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"
gcloud artifacts repositories add-iam-policy-binding buildtrace-repo \
  --location=$REGION \
  --member="serviceAccount:$DEFAULT_CB_SA" \
  --role="roles/artifactregistry.writer"
```

**Step 4: Create Additional Repositories (Optional)**
```bash
# Create repository for base images
gcloud artifacts repositories create buildtrace-base-images \
  --repository-format=docker \
  --location=$REGION \
  --description="Base images for BuildTrace"

# Create repository for third-party images
gcloud artifacts repositories create buildtrace-third-party \
  --repository-format=docker \
  --location=$REGION \
  --description="Third-party container images"
```

---

### 1.9 Secret Manager Setup

#### Task: Store Secrets Securely

**Step 1: Create Secrets**
```bash
# Database passwords (already created above)
# gcloud secrets create db-root-password --data-file=-
# gcloud secrets create db-user-password --data-file=-

# OpenAI API key
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Auth provider secrets
echo -n "YOUR_AUTH_SECRET" | gcloud secrets create auth-provider-secret \
  --data-file=- \
  --replication-policy="automatic"

# JWT signing key
openssl rand -base64 32 | gcloud secrets create jwt-signing-key \
  --data-file=- \
  --replication-policy="automatic"

# Other API keys
echo -n "YOUR_OTHER_API_KEY" | gcloud secrets create other-api-key \
  --data-file=- \
  --replication-policy="automatic"
```

**Step 2: Grant Access to Secrets**
```bash
# Grant service account access to secrets
gcloud secrets add-iam-policy-binding db-user-password \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Grant to GKE workload service account
gcloud secrets add-iam-policy-binding db-user-password \
  --member="serviceAccount:$GKE_WORKLOAD_SA" \
  --role="roles/secretmanager.secretAccessor"
```

**Step 3: Create Secret Versions**
```bash
# Update secret (creates new version)
echo -n "NEW_VALUE" | gcloud secrets versions add secret-name \
  --data-file=-

# List secret versions
gcloud secrets versions list secret-name

# Access secret value
gcloud secrets versions access latest --secret="secret-name"
```

---

### 1.10 VPC and Networking Setup

#### Task: Configure Network (If Not Using Default)

**Step 1: Create Custom VPC (Optional)**
```bash
# Create VPC network
gcloud compute networks create buildtrace-vpc \
  --subnet-mode=custom \
  --bgp-routing-mode=regional

# Create subnet
gcloud compute networks subnets create buildtrace-subnet \
  --network=buildtrace-vpc \
  --range=10.0.0.0/16 \
  --region=$REGION \
  --enable-private-ip-google-access

# Create firewall rules
gcloud compute firewall-rules create allow-internal \
  --network=buildtrace-vpc \
  --allow=tcp,udp,icmp \
  --source-ranges=10.0.0.0/16

gcloud compute firewall-rules create allow-ssh \
  --network=buildtrace-vpc \
  --allow=tcp:22 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=ssh
```

**Step 2: Configure Cloud NAT (for private GKE nodes)**
```bash
# Create Cloud Router
gcloud compute routers create buildtrace-router \
  --network=buildtrace-vpc \
  --region=$REGION

# Create NAT gateway
gcloud compute routers nats create buildtrace-nat \
  --router=buildtrace-router \
  --region=$REGION \
  --nat-all-subnet-ip-ranges \
  --auto-allocate-nat-external-ips
```

---

## Phase 2: During Development - Development Resources

### 2.1 Development Environment Setup

#### Task: Create Development Project and Resources

**Step 1: Create Development Project**
```bash
# Create dev project
gcloud projects create buildtrace-dev --name="BuildTrace Development"

# Set as current project
gcloud config set project buildtrace-dev

# Enable billing
# Link billing account via console or:
# gcloud billing projects link buildtrace-dev --billing-account=BILLING_ACCOUNT_ID

# Enable APIs (same as production)
gcloud services enable \
  run.googleapis.com \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  storage-component.googleapis.com \
  sqladmin.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  secretmanager.googleapis.com
```

**Step 2: Create Development Resources**
```bash
# Create dev storage buckets
gsutil mb -p buildtrace-dev -c STANDARD -l $REGION gs://buildtrace-dev-input
gsutil mb -p buildtrace-dev -c STANDARD -l $REGION gs://buildtrace-dev-processed
gsutil mb -p buildtrace-dev -c STANDARD -l $REGION gs://buildtrace-dev-artifacts

# Create dev database (smaller instance)
gcloud sql instances create buildtrace-dev-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-type=SSD \
  --storage-size=10GB

# Create dev Pub/Sub topics
gcloud pubsub topics create buildtrace-dev-ocr-queue
gcloud pubsub topics create buildtrace-dev-diff-queue
gcloud pubsub topics create buildtrace-dev-summary-queue

# Create dev Artifact Registry
gcloud artifacts repositories create buildtrace-dev-repo \
  --repository-format=docker \
  --location=$REGION
```

**Step 3: Create Staging Environment**
```bash
# Similar setup for staging
gcloud projects create buildtrace-staging --name="BuildTrace Staging"
# ... repeat resource creation with "staging" prefix
```

---

### 2.2 CI/CD Pipeline Setup

#### Task: Configure Cloud Build

**Step 1: Create Cloud Build Triggers**

**Via Console:**
1. Navigate to "Cloud Build" > "Triggers"
2. Click "CREATE TRIGGER"
3. Configure:
   - Name: `buildtrace-api-build`
   - Event: Push to a branch
   - Source: Connect repository (GitHub/GitLab/Bitbucket)
   - Branch: `^main$` (or `^develop$` for dev)
   - Configuration: Cloud Build configuration file
   - Location: `cloudbuild.yaml` (or path to your build file)
4. Click "CREATE"

**Step 2: Create cloudbuild.yaml**
```yaml
# cloudbuild.yaml
steps:
  # Build API image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'Dockerfile.api'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-api:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-api:latest'
      - '.'

  # Build Worker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'Dockerfile.worker'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-worker:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-worker:latest'
      - '.'

  # Push API image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-api'

  # Push Worker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-worker'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'buildtrace-api'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/buildtrace-repo/buildtrace-api:${SHORT_SHA}'
      - '--region'
      - '${_REGION}'
      - '--platform'
      - 'managed'

substitutions:
  _REGION: 'us-west2'

options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY
```

**Step 3: Create Separate Triggers for Each Service**
```bash
# Create trigger for API
gcloud builds triggers create github \
  --name="buildtrace-api-trigger" \
  --repo-name="buildtrace" \
  --repo-owner="YOUR_GITHUB_USER" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild-api.yaml"

# Create trigger for Workers
gcloud builds triggers create github \
  --name="buildtrace-worker-trigger" \
  --repo-name="buildtrace" \
  --repo-owner="YOUR_GITHUB_USER" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild-worker.yaml"
```

**Step 4: Configure Build Substitutions**
```bash
# Set default substitutions
gcloud builds triggers update buildtrace-api-trigger \
  --substitutions="_REGION=us-west2,_ENV=production"
```

---

### 2.3 Local Development Setup

#### Task: Configure Local Development Environment

**Step 1: Install Required Tools**
```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Install kubectl
gcloud components install kubectl

# Install Cloud SQL Proxy
# https://cloud.google.com/sql/docs/postgres/sql-proxy

# Install Docker
# https://docs.docker.com/get-docker/
```

**Step 2: Configure Local Authentication**
```bash
# Authenticate with GCP
gcloud auth login

# Set application default credentials
gcloud auth application-default login

# Or use service account key
export GOOGLE_APPLICATION_CREDENTIALS="./buildtrace-key.json"
```

**Step 3: Set Up Local Database Connection**
```bash
# Start Cloud SQL Proxy
cloud_sql_proxy -instances=$DB_CONNECTION_NAME=tcp:5432 &

# Connect to database
psql "host=127.0.0.1 port=5432 dbname=buildtrace_db user=buildtrace_user"
```

**Step 4: Configure Local Environment Variables**
```bash
# Create .env file
cat > .env.local << EOF
PROJECT_ID=$PROJECT_ID
REGION=$REGION
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=buildtrace_db
DB_USER=buildtrace_user
DB_PASS=$(gcloud secrets versions access latest --secret="db-user-password")
INPUT_BUCKET=buildtrace-prod-input-$PROJECT_ID
PROCESSED_BUCKET=buildtrace-prod-processed-$PROJECT_ID
ARTIFACTS_BUCKET=buildtrace-prod-artifacts-$PROJECT_ID
PUBSUB_OCR_TOPIC=buildtrace-prod-ocr-queue
PUBSUB_DIFF_TOPIC=buildtrace-prod-diff-queue
PUBSUB_SUMMARY_TOPIC=buildtrace-prod-summary-queue
EOF

# Load environment variables
source .env.local
```

---

### 2.4 Testing Infrastructure

#### Task: Set Up Testing Resources

**Step 1: Create Test Data Buckets**
```bash
# Create test bucket
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-test-data

# Upload test files
gsutil cp test-data/*.pdf gs://buildtrace-test-data/
```

**Step 2: Create Test Database**
```bash
# Create test database instance (small)
gcloud sql instances create buildtrace-test-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-type=SSD \
  --storage-size=10GB

# Create test database
gcloud sql databases create buildtrace_test_db --instance=buildtrace-test-db
```

**Step 3: Set Up Test Pub/Sub Topics**
```bash
# Create test topics
gcloud pubsub topics create buildtrace-test-ocr-queue
gcloud pubsub topics create buildtrace-test-diff-queue
gcloud pubsub topics create buildtrace-test-summary-queue

# Create test subscriptions
gcloud pubsub subscriptions create buildtrace-test-ocr-sub \
  --topic=buildtrace-test-ocr-queue
```

---

## Phase 3: After Development - Production & Monitoring

### 3.1 Monitoring Setup

#### Task: Configure Cloud Monitoring

**Step 1: Create Custom Metrics**

**Via Console:**
1. Navigate to "Monitoring" > "Metrics Explorer"
2. Click "CREATE METRIC"
3. Configure custom metrics for:
   - Job processing latency
   - Job success/failure rates
   - Queue depth
   - Worker utilization
   - API request latency
   - Error rates by service

**Via Code (Example):**
```python
from google.cloud import monitoring_v3

client = monitoring_v3.MetricServiceClient()
project_name = f"projects/{PROJECT_ID}"

# Create custom metric descriptor
descriptor = monitoring_v3.MetricDescriptor()
descriptor.type = "custom.googleapis.com/buildtrace/job_latency"
descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.GAUGE
descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.DOUBLE
descriptor.description = "Job processing latency in milliseconds"

client.create_metric_descriptor(
    name=project_name, metric_descriptor=descriptor
)
```

**Step 2: Create Monitoring Dashboards**

**Via Console:**
1. Navigate to "Monitoring" > "Dashboards"
2. Click "CREATE DASHBOARD"
3. Create widgets for:
   - System Health Overview
   - Job Processing Metrics
   - API Performance
   - Error Rates
   - Resource Utilization
   - Cost Metrics

**Via API (JSON Configuration):**
```json
{
  "displayName": "BuildTrace System Health",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Job Processing Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" metric.type=\"run.googleapis.com/request_count\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
```

**Step 3: Set Up Log-Based Metrics**
```bash
# Create log-based metric for errors
gcloud logging metrics create buildtrace_error_count \
  --description="Count of BuildTrace errors" \
  --log-filter='resource.type="cloud_run_revision" severity>=ERROR'

# Create log-based metric for job completions
gcloud logging metrics create buildtrace_job_completed \
  --description="Count of completed jobs" \
  --log-filter='jsonPayload.event="job_completed"'
```

---

### 3.2 Alerting Setup

#### Task: Configure Alerting Policies

**Step 1: Create Alert Policies**

**Via Console:**
1. Navigate to "Monitoring" > "Alerting" > "Policies"
2. Click "CREATE POLICY"
3. Configure alerts for:
   - High error rate (> 5% of requests)
   - Job processing failures (> 10 failures in 5 minutes)
   - High latency (P95 > 10 seconds)
   - Queue depth (backlog > 1000 messages)
   - Service unavailability (uptime < 99%)
   - Database connection failures
   - Storage quota warnings (> 80% full)
   - Cost anomalies

**Via gcloud CLI:**
```bash
# Create alert policy JSON
cat > alert-policy.json << EOF
{
  "displayName": "High Error Rate",
  "conditions": [{
    "displayName": "Error rate exceeds threshold",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" metric.type=\"run.googleapis.com/request_count\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0.05,
      "duration": "300s"
    }
  }],
  "notificationChannels": ["projects/$PROJECT_ID/notificationChannels/CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

# Create alert policy
gcloud alpha monitoring policies create --policy-from-file=alert-policy.json
```

**Step 2: Create Notification Channels**
```bash
# Create email notification channel
gcloud alpha monitoring channels create \
  --display-name="BuildTrace Alerts" \
  --type=email \
  --channel-labels=email_address=alerts@buildtrace.ai

# Create Slack notification channel (requires webhook URL)
gcloud alpha monitoring channels create \
  --display-name="BuildTrace Slack" \
  --type=slack \
  --channel-labels=url=YOUR_SLACK_WEBHOOK_URL

# Create PagerDuty channel
gcloud alpha monitoring channels create \
  --display-name="BuildTrace PagerDuty" \
  --type=pagerduty \
  --channel-labels=service_key=YOUR_PAGERDUTY_KEY
```

**Step 3: Create Uptime Checks**
```bash
# Create HTTP uptime check
gcloud monitoring uptime-checks create buildtrace-api-health \
  --display-name="BuildTrace API Health Check" \
  --http-check-path="/health" \
  --http-check-port=443 \
  --http-check-use-ssl \
  --resource-type=uptime-url \
  --timeout=10s \
  --period=60s

# Create TCP uptime check (for database)
gcloud monitoring uptime-checks create buildtrace-db-health \
  --display-name="BuildTrace Database Health" \
  --tcp-check-port=5432 \
  --resource-type=uptime-url \
  --timeout=10s \
  --period=300s
```

---

### 3.3 Logging Configuration

#### Task: Set Up Structured Logging

**Step 1: Configure Log Sinks**
```bash
# Create log sink to BigQuery (for analytics)
gcloud logging sinks create buildtrace-bigquery-sink \
  bigquery.googleapis.com/projects/$PROJECT_ID/datasets/buildtrace_logs \
  --log-filter='resource.type="cloud_run_revision"'

# Create log sink to Cloud Storage (for archival)
gcloud logging sinks create buildtrace-storage-sink \
  storage.googleapis.com/buildtrace-prod-logs-$PROJECT_ID \
  --log-filter='resource.type="cloud_run_revision"'

# Create log sink to Pub/Sub (for real-time processing)
gcloud logging sinks create buildtrace-pubsub-sink \
  pubsub.googleapis.com/projects/$PROJECT_ID/topics/buildtrace-logs \
  --log-filter='severity>=WARNING'
```

**Step 2: Configure Log Retention**
```bash
# Set log retention policy (30 days default, can be extended)
# This is done via console:
# 1. Navigate to "Logging" > "Logs Router"
# 2. Click on sink
# 3. Configure retention period
```

**Step 3: Set Up Log Exports**
```bash
# Export logs to BigQuery dataset
bq mk --dataset buildtrace_logs

# Create log-based views in BigQuery
bq query --use_legacy_sql=false << EOF
CREATE VIEW \`$PROJECT_ID.buildtrace_logs.error_logs\` AS
SELECT
  timestamp,
  severity,
  jsonPayload.message,
  jsonPayload.job_id,
  resource.labels.service_name
FROM
  \`$PROJECT_ID.buildtrace_logs.cloud_run_revision\`
WHERE
  severity >= "ERROR"
EOF
```

---

### 3.4 Error Reporting Setup

#### Task: Configure Error Reporting

**Step 1: Enable Error Reporting**
```bash
# Error Reporting is automatically enabled with Cloud Logging
# Errors are automatically collected from:
# - Cloud Run services
# - GKE applications
# - Any application using Cloud Logging
```

**Step 2: Configure Error Grouping**
```bash
# Errors are automatically grouped by:
# - Error message
# - Stack trace
# - Source location
# - Service name

# View errors via console:
# Navigate to "Error Reporting" > "Errors"
```

**Step 3: Set Up Error Notifications**
```bash
# Create notification channel for errors
gcloud alpha monitoring channels create \
  --display-name="Error Alerts" \
  --type=email \
  --channel-labels=email_address=errors@buildtrace.ai

# Create alert policy for new error types
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="New Error Type Detected" \
  --condition-display-name="Error count > 0" \
  --condition-threshold-value=1
```

---

### 3.5 Performance Monitoring

#### Task: Set Up APM and Performance Monitoring

**Step 1: Enable Cloud Trace (Distributed Tracing)**
```bash
# Cloud Trace is automatically enabled for Cloud Run
# For custom instrumentation, use OpenTelemetry or Cloud Trace API

# Install OpenTelemetry
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation

# Configure in application
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

cloud_trace_exporter = CloudTraceSpanExporter()
span_processor = BatchSpanProcessor(cloud_trace_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
```

**Step 2: Create Performance Dashboards**
```bash
# Create dashboard for:
# - Request latency (P50, P95, P99)
# - Throughput (requests per second)
# - Error rates
# - Database query performance
# - Pub/Sub message processing time
```

**Step 3: Set Up Profiling (Cloud Profiler)**
```bash
# Enable Cloud Profiler for Python
pip install google-cloud-profiler

# Initialize profiler in application
import googlecloudprofiler

googlecloudprofiler.start(
    service='buildtrace-api',
    service_version='1.0.0',
    verbose=1,
)
```

---

### 3.6 Cost Monitoring

#### Task: Set Up Cost Monitoring and Optimization

**Step 1: Create Cost Dashboard**
```bash
# Navigate to "Billing" > "Reports"
# Create custom reports for:
# - Service-level costs
# - Resource-level costs
# - Cost trends over time
# - Budget alerts
```

**Step 2: Set Up Budget Alerts**
```bash
# Create budget
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="BuildTrace Monthly Budget" \
  --budget-amount=1000USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100

# Create budget alert
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="BuildTrace Alert Budget" \
  --budget-amount=500USD \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100 \
  --notifications-rule=pubsub-topic=projects/$PROJECT_ID/topics/budget-alerts
```

**Step 3: Enable Cost Allocation Tags**
```bash
# Add labels to resources for cost tracking
gcloud run services update buildtrace-api \
  --update-labels=environment=production,team=engineering,cost-center=product

# View costs by label
# Navigate to "Billing" > "Reports" > Filter by labels
```

---

### 3.7 Security Monitoring

#### Task: Set Up Security Monitoring

**Step 1: Enable Security Command Center (if available)**
```bash
# Enable Security Command Center (Enterprise only)
# Navigate to "Security Command Center" > "Settings"
# Enable asset discovery and threat detection
```

**Step 2: Set Up Audit Logs**
```bash
# Audit logs are automatically enabled
# View via: "IAM & Admin" > "Audit Logs"

# Create log sink for audit logs
gcloud logging sinks create audit-logs-sink \
  bigquery.googleapis.com/projects/$PROJECT_ID/datasets/audit_logs \
  --log-filter='logName:"cloudaudit.googleapis.com"'
```

**Step 3: Configure Security Alerts**
```bash
# Create alert for failed authentication attempts
gcloud alpha monitoring policies create \
  --display-name="Failed Authentication Alert" \
  --condition-threshold-value=10 \
  --condition-filter='resource.type="cloud_run_revision" jsonPayload.statusCode=401'

# Create alert for unusual API usage
gcloud alpha monitoring policies create \
  --display-name="Unusual API Usage" \
  --condition-threshold-value=1000 \
  --condition-filter='resource.type="cloud_run_revision" metric.type="run.googleapis.com/request_count"'
```

---

### 3.8 Maintenance and Operations

#### Task: Set Up Operational Procedures

**Step 1: Create Runbooks**
```bash
# Document procedures for:
# - Service deployment
# - Database migrations
# - Rollback procedures
# - Incident response
# - Capacity planning
```

**Step 2: Set Up Automated Backups**
```bash
# Cloud SQL automatic backups are enabled
# Configure backup retention
gcloud sql instances patch buildtrace-prod-db \
  --backup-start-time=02:00 \
  --enable-bin-log \
  --retained-backups-count=7

# Create manual backup
gcloud sql backups create \
  --instance=buildtrace-prod-db \
  --description="Pre-deployment backup"
```

**Step 3: Set Up Maintenance Windows**
```bash
# Configure maintenance windows for Cloud SQL
gcloud sql instances patch buildtrace-prod-db \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=3

# Schedule maintenance tasks
# Use Cloud Scheduler for periodic tasks
gcloud scheduler jobs create http backup-job \
  --schedule="0 2 * * 0" \
  --uri="https://buildtrace-api-XXXXX.run.app/api/v1/admin/backup" \
  --http-method=POST \
  --oidc-service-account-email=$SERVICE_ACCOUNT_EMAIL
```

---

## Quick Reference Commands

### Project Management
```bash
# List all projects
gcloud projects list

# Set active project
gcloud config set project $PROJECT_ID

# Get project info
gcloud projects describe $PROJECT_ID
```

### Service Management
```bash
# List Cloud Run services
gcloud run services list --region=$REGION

# View service details
gcloud run services describe SERVICE_NAME --region=$REGION

# View service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME" --limit=50

# Update service
gcloud run services update SERVICE_NAME --memory=1Gi --region=$REGION
```

### Database Management
```bash
# List Cloud SQL instances
gcloud sql instances list

# Connect to database
gcloud sql connect INSTANCE_NAME --user=USER_NAME --database=DATABASE_NAME

# Create database backup
gcloud sql backups create --instance=INSTANCE_NAME

# List backups
gcloud sql backups list --instance=INSTANCE_NAME
```

### Monitoring
```bash
# View metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"'

# List alert policies
gcloud alpha monitoring policies list

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

---

## Cost Estimation

### Monthly Cost Estimate (Production)

**Compute:**
- Cloud Run API: ~$50-200/month (depending on traffic)
- Cloud Run Workers: ~$100-500/month
- GKE Cluster (if used): ~$200-1000/month

**Storage:**
- Cloud Storage: ~$20-100/month (depending on data volume)
- Cloud SQL: ~$100-500/month (depending on instance size)

**Networking:**
- Egress: ~$10-50/month

**Other Services:**
- Pub/Sub: ~$10-30/month
- Cloud Build: ~$10-50/month
- Monitoring/Logging: ~$20-100/month

**Total Estimated: ~$520-2,530/month**

### Cost Optimization Tips
1. Use Cloud Run instead of GKE for serverless workloads
2. Enable autoscaling to scale down during low usage
3. Use lifecycle policies to move old data to cheaper storage classes
4. Monitor and optimize database instance size
5. Use committed use discounts for predictable workloads
6. Enable Cloud CDN for static content
7. Use Cloud SQL read replicas instead of larger primary instances

---

## Security Checklist

### Pre-Deployment
- [ ] All service accounts have minimum required permissions
- [ ] Secrets stored in Secret Manager, not in code
- [ ] Database connections use private IP or Cloud SQL Proxy
- [ ] All buckets are private (no public access)
- [ ] IAM policies reviewed and documented
- [ ] Network policies configured (if using GKE)
- [ ] SSL/TLS enabled for all external endpoints
- [ ] CORS configured appropriately

### Post-Deployment
- [ ] Monitoring and alerting configured
- [ ] Log retention policies set
- [ ] Backup procedures tested
- [ ] Incident response plan documented
- [ ] Security updates scheduled
- [ ] Access logs reviewed regularly
- [ ] Cost budgets and alerts configured

---

## Conclusion

This comprehensive GCP resource plan covers all aspects of setting up, developing, and maintaining the BuildTrace system on Google Cloud Platform. Follow each phase sequentially, and adjust configurations based on your specific requirements and scale.

For detailed implementation steps, refer to:
- `DETAILED_IMPLEMENTATION_GUIDE.md` - Step-by-step implementation
- `SHORT_IMPLEMENTATION.md` - Quick reference guide
- `architecture.md` - System architecture
- `architecture2.md` - Detailed architecture with Pub/Sub

---

_End of Document_

