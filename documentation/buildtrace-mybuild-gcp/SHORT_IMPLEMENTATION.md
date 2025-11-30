# BuildTrace System - Short Implementation Guide

## Table of Contents
1. [Phase 1: GCP Console Setup & Infrastructure](#phase-1-gcp-console-setup--infrastructure)
2. [Phase 2: Application Development](#phase-2-application-development)
3. [Phase 3: Containerization & Deployment](#phase-3-containerization--deployment)
4. [Phase 4: Testing & Validation](#phase-4-testing--validation)
5. [Phase 5: Documentation & Delivery](#phase-5-documentation--delivery)
6. [Phase 6: Stretch Goals](#phase-6-stretch-goals)

---

## Phase 1: GCP Console Setup & Infrastructure

### 1.1 GCP Project Setup

**Steps:**
1. Create or select GCP project named `buildtrace-system`
2. Enable billing for the project
3. Set IAM permissions (Owner or Editor + Security Admin)
4. Set environment variables: `PROJECT_ID`, `PROJECT_NUMBER`, `REGION`

### 1.2 Enable Required GCP APIs

**Required APIs:**
- Cloud Run Admin API (`run.googleapis.com`)
- Cloud Pub/Sub API (`pubsub.googleapis.com`)
- Cloud Tasks API (`cloudtasks.googleapis.com`)
- Cloud Storage API (`storage-component.googleapis.com`)
- Cloud SQL Admin API (`sqladmin.googleapis.com`) OR BigQuery API
- Cloud Build API (`cloudbuild.googleapis.com`)
- Artifact Registry API (`artifactregistry.googleapis.com`)

**Enable via gcloud CLI:**
```bash
gcloud services enable run.googleapis.com pubsub.googleapis.com cloudtasks.googleapis.com storage-component.googleapis.com sqladmin.googleapis.com bigquery.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### 1.3 Cloud Storage Setup

**Tasks:**
1. Create input bucket: `buildtrace-input-{project-id}`
2. Create output bucket: `buildtrace-output-{project-id}`
3. Create folder structure: `input/`, `processed/`, `failed/` in input bucket; `results/`, `metrics/` in output bucket
4. Set bucket permissions (private, service account access only)
5. Configure lifecycle policy (optional: auto-delete after 90 days)

### 1.4 Database Setup

#### Option A: Cloud SQL (PostgreSQL)

**Steps:**
1. Create Cloud SQL instance: `buildtrace-db` (PostgreSQL 15, db-f1-micro for testing)
2. Create database: `buildtrace_db`
3. Create database user: `buildtrace_user`
4. Create schema with tables:
   - `drawing_pairs` - tracks drawing version pairs
   - `change_results` - stores detected changes
   - `processing_metrics` - stores processing metrics
   - `anomalies` - stores detected anomalies
5. Create indexes on frequently queried columns

#### Option B: BigQuery

**Steps:**
1. Create BigQuery dataset: `buildtrace`
2. Create tables with same schema as Cloud SQL option

### 1.5 Pub/Sub Setup

**Tasks:**
1. Create main topic: `drawing-processing-tasks`
2. Create dead-letter topic: `drawing-processing-dlq`
3. Create push subscription: `drawing-processing-workers` (configure after worker deployment)
   - Push endpoint: Cloud Run worker URL
   - Ack deadline: 600 seconds
   - Max delivery attempts: 5
   - Dead letter topic enabled
4. Create dead-letter subscription: `drawing-processing-dlq-sub`

### 1.6 Cloud Tasks Setup (Alternative to Pub/Sub)

**Optional:** Create Cloud Tasks queue `drawing-processing-queue` with retry configuration (max attempts: 5, backoff settings)

### 1.7 Service Account Setup

**Steps:**
1. Create service account: `buildtrace-service-account`
2. Grant required roles:
   - `roles/run.invoker`
   - `roles/storage.objectAdmin`
   - `roles/pubsub.subscriber` and `roles/pubsub.publisher`
   - `roles/cloudsql.client` (for Cloud SQL) OR `roles/bigquery.dataEditor` (for BigQuery)
   - `roles/logging.logWriter`
3. Generate service account key for local testing (add to `.gitignore`)

### 1.8 Artifact Registry Setup

**Steps:**
1. Create Docker repository: `buildtrace-repo` (format: Docker, location: same as project region)
2. Configure Docker authentication for Artifact Registry
3. Grant Cloud Build service account `roles/artifactregistry.writer` permission

---

## Phase 2: Application Development

### 2.1 Project Structure Setup

**Directory Structure:**
```
buildtrace/
├── api/              # FastAPI application
│   ├── main.py       # FastAPI app entry point
│   ├── routers/      # API endpoints (process, changes, metrics, health)
│   ├── models/       # Data models (drawing, changes)
│   └── utils/        # Utilities (database, pubsub, error_handler)
├── workers/          # Worker service
│   ├── main.py       # Worker entry point
│   └── processor.py  # Change detection logic
├── simulators/       # Test data generator
├── infra/            # Infrastructure scripts
├── tests/            # Unit tests
├── Dockerfile.api
├── Dockerfile.worker
└── requirements.txt
```

### 2.2 Core Change Detection Logic

**Components:**
- **Models:** `DrawingObject`, `DrawingVersion`, `ChangeResult` (Pydantic models)
- **Processor:** 
  - `parse_drawing_json()` - Parse JSON into DrawingVersion
  - `detect_changes()` - Compare two versions and detect:
    - Added objects (in B but not in A)
    - Removed objects (in A but not in B)
    - Moved objects (same ID, different position)
  - `generate_summary()` - Generate natural language summary
- **Validation:** Validate JSON structure and required fields

### 2.3 API Endpoints (FastAPI)

**Endpoints:**
- **POST /process** - Accept drawing version pairs, queue for processing via Pub/Sub
- **GET /changes?drawing_id={id}** - Retrieve detected changes for a drawing
- **GET /metrics** - Return processing metrics (hourly stats, P95/P99 latency, data quality issues)
- **GET /health** - Health check with anomaly detection

**Key Features:**
- CORS middleware enabled
- Environment variable configuration
- Error handling and validation

### 2.4 Worker Implementation

**Components:**
- **POST /process-drawing** - Pub/Sub push endpoint
- **Functions:**
  - `load_from_storage()` - Load drawing versions from Cloud Storage
  - `store_results()` - Store change results in database
  - `store_metrics()` - Store processing metrics
  - `check_anomalies()` - Detect and store anomalies
  - `store_error()` - Handle and log errors

**Processing Flow:**
1. Receive Pub/Sub message
2. Load drawing versions (from message or Cloud Storage)
3. Detect changes using processor
4. Store results in database
5. Update metrics
6. Check for anomalies

### 2.5 Metrics & Analytics

**Metrics Collected:**
- Processing latency (milliseconds)
- Change counts (added, removed, moved)
- Status (completed, error)
- Hourly aggregations
- P95 and P99 latency percentiles

**Implementation:**
- Metrics stored in `processing_metrics` table
- Aggregation functions for hourly stats and percentiles

### 2.6 Anomaly Detection

**Anomaly Types:**
- **Spike Detection:** 10x increase in change count for a drawing
- **Missing Uploads:** Delayed processing (pending > 2 hours)
- **Processing Errors:** Failed processing attempts

**Implementation:**
- Anomalies stored in `anomalies` table
- Checked during processing and health checks

### 2.7 Data Simulator

**Functions:**
- `generate_drawing_object()` - Generate single drawing object
- `generate_drawing_version()` - Generate complete drawing version
- `generate_drawing_pair()` - Generate pair with changes
- `generate_batch()` - Generate batch of pairs
- `upload_to_cloud_storage()` - Upload to Cloud Storage

### 2.8 Error Handling & Data Quality

**Components:**
- `DataQualityError` exception class
- `validate_json_structure()` - Validate JSON format
- `handle_processing_error()` - Log and store errors
- Error logging to Cloud Logging
- Error storage in anomalies table

---

## Phase 3: Containerization & Deployment

### 3.1 Docker Configuration

**Dockerfiles:**
- **Dockerfile.api:** Python 3.11-slim, installs dependencies, runs FastAPI with uvicorn
- **Dockerfile.worker:** Similar to API, runs worker service

**Requirements:**
- FastAPI, uvicorn, pydantic
- Google Cloud client libraries (storage, pubsub, tasks)
- Database connectors (psycopg2, cloud-sql-connector)
- python-dotenv

### 3.2 Cloud Run Deployment - API Service

**Steps:**
1. Build Docker image and push to Artifact Registry
2. Deploy to Cloud Run with:
   - Service name: `buildtrace-api`
   - Memory: 512Mi
   - CPU: 1
   - Min instances: 0, Max instances: 10
   - Concurrency: 80
   - Timeout: 300 seconds
   - Cloud SQL connection enabled
   - Environment variables configured

### 3.3 Cloud Run Deployment - Worker Service

**Steps:**
1. Build worker Docker image
2. Deploy to Cloud Run with:
   - Service name: `buildtrace-worker`
   - Memory: 1Gi
   - CPU: 2
   - Min instances: 0, Max instances: 20
   - Concurrency: 10
   - Timeout: 900 seconds
   - Authentication: Not publicly accessible (Pub/Sub only)
   - Cloud SQL connection enabled

### 3.4 Pub/Sub Subscription Configuration

**Steps:**
1. Grant Pub/Sub service account permission to invoke Cloud Run worker
2. Create/update push subscription with worker URL as endpoint
3. Configure dead-letter queue settings

### 3.5 IAM & Permissions

**Verification:**
- Verify service account has all required roles
- Ensure Pub/Sub can invoke worker service
- Check Cloud SQL connection permissions

---

## Phase 4: Testing & Validation

### 4.1 Local Testing

**Tests:**
- Test change detection logic with sample data
- Test API endpoints locally with environment variables set
- Validate JSON parsing and error handling

### 4.2 Cloud Testing

**Endpoint Tests:**
- POST /process - Submit drawing pairs
- GET /changes - Retrieve changes
- GET /metrics - Check metrics
- GET /health - Health check

### 4.3 Load Testing

**Steps:**
1. Generate large batch of test data (1000+ pairs)
2. Upload to Cloud Storage
3. Submit batch via API
4. Monitor Cloud Run metrics and logs
5. Verify processing completes successfully

---

## Phase 5: Documentation & Delivery

### 5.1 README.md

**Contents:**
- System architecture diagram
- Data flow explanation
- Scaling strategy
- Fault tolerance approach
- Metrics computation methodology
- Trade-offs and design decisions

### 5.2 Deployment Scripts

**Create deployment script** (`infra/deploy.sh`) that:
- Builds and pushes Docker images
- Deploys API and worker services
- Configures Pub/Sub subscriptions
- Verifies deployment

---

## Phase 6: Stretch Goals

### 6.1 BigQuery Integration

Use BigQuery for metrics aggregation on hourly basis for better performance with large datasets.

### 6.2 Dashboard

Create monitoring dashboard in GCP Console using custom metrics with thresholds and alert readiness.

### 6.3 Logging

Implement structured logging throughout the application for better observability.

### 6.4 Pub/Sub Dead-Letter Queue

Dead-letter queue is implemented and configured. Messages that fail after max delivery attempts are routed to DLQ.

---

## Quick Reference Commands

```bash
# Set project
gcloud config set project $PROJECT_ID

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Check service status
gcloud run services list

# Update service
gcloud run services update buildtrace-api --memory 1Gi --region=$REGION
```

---

This guide provides a high-level overview of the BuildTrace system implementation. Refer to the detailed implementation guide for specific code examples and detailed configurations.

