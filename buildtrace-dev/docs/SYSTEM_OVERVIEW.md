# BuildTrace System Overview

**Version:** 2.1.0  
**Last Updated:** November 29, 2025 (Evening)  
**Status:** ✅ Production-Ready | Workers Fully Operational

---

## Executive Summary

BuildTrace is a **cloud-native SaaS platform** for automated construction drawing comparison and change detection. The system processes architectural drawings (PDFs) through AI-powered OCR, computer vision-based diff calculation, and LLM-generated summaries to identify, visualize, and document changes between drawing versions.

### Key Capabilities

- ✅ **Automated Drawing Comparison** - Upload PDFs, automatic OCR, diff generation
- ✅ **AI-Powered Analysis** - Change detection using GPT-4o Vision
- ✅ **Real-time Processing** - Async job orchestration with Pub/Sub workers
- ✅ **Multi-tenant Support** - Organization-based project management
- ✅ **OAuth Authentication** - Google Cloud Identity integration
- ✅ **Cloud-Native** - Fully deployed on Google Cloud Platform
- ✅ **Scalable Architecture** - Horizontal scaling with Cloud Run + GKE workers
- ✅ **End-to-End Pipeline** - Fully operational (tested Nov 29, 2025)

---

## 🎉 Milestone: End-to-End Pipeline Working!

**Date:** November 29, 2025

The complete BuildTrace pipeline is now operational:
- ✅ OCR workers processing with GPT-4o (~40-60 sec/page)
- ✅ Diff workers processing with SIFT alignment (28GB memory)
- ✅ Summary workers generating AI summaries
- ✅ Full job completed successfully

---

## Repository Structure

```
buildtrace-dev/
├── backend/                    # Python Flask API
│   ├── app.py                 # Flask application entry
│   ├── config.py              # Configuration management
│   ├── blueprints/            # API route handlers
│   │   ├── auth.py           # OAuth & JWT authentication
│   │   ├── drawings.py       # Drawing upload endpoints
│   │   ├── jobs.py           # Job management endpoints
│   │   ├── projects.py       # Project CRUD
│   │   ├── overlays.py       # Overlay management
│   │   ├── summaries.py      # Summary management
│   │   └── chat.py           # Chatbot API (implemented)
│   ├── services/             # Business logic services
│   │   ├── orchestrator.py  # Job orchestration
│   │   ├── drawing_service.py # Upload handling
│   │   ├── chatbot_service.py # AI chatbot
│   │   └── context_retriever.py # Context extraction
│   ├── processing/           # Processing pipelines
│   │   ├── ocr_pipeline.py  # OCR extraction (GPT-4o)
│   │   ├── diff_pipeline.py # Change detection (SIFT)
│   │   └── summary_pipeline.py # AI summarization
│   ├── workers/              # Pub/Sub workers
│   │   ├── ocr_worker.py    # OCR task processor
│   │   ├── diff_worker.py   # Diff task processor
│   │   ├── summary_worker.py # Summary task processor
│   │   └── *_worker_entry.py # GKE entry points
│   ├── gcp/                  # GCP integrations
│   │   ├── database/        # Cloud SQL models
│   │   ├── storage/         # GCS storage service
│   │   └── pubsub/          # Pub/Sub client
│   ├── utils/               # Utility functions
│   └── tests/               # Test suite
├── frontend/                  # Next.js React application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Next.js pages
│   │   ├── lib/             # API client
│   │   └── store/           # Zustand state
│   └── public/              # Static assets
├── k8s/                      # Kubernetes manifests
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── ocr-worker-deployment.yaml
│   ├── diff-worker-deployment.yaml
│   └── summary-worker-deployment.yaml
├── scripts/                  # Deployment scripts
│   ├── deploy-workers-gke.sh
│   ├── fix-image-pull.sh
│   └── verify-pubsub.sh
└── docs/                     # Documentation
    ├── SYSTEM_OVERVIEW.md    # This file
    ├── ARCHITECTURE.md       # System architecture
    ├── PROGRESS.md           # Implementation status
    └── PENDING.md            # Remaining tasks
```

---

## System Flow

### 1. User Upload Flow

```
User → Frontend (Upload Page)
  ↓
POST /api/v1/drawings/upload (old PDF)
  ↓
DrawingUploadService
  ├── Validates file (size, type)
  ├── Uploads to GCS bucket
  ├── Creates DrawingVersion record
  └── Returns drawing_version_id_1
  ↓
POST /api/v1/drawings/upload (new PDF, with old_version_id)
  ↓
DrawingUploadService (same process)
  └── Returns drawing_version_id_2
  ↓
POST /api/v1/jobs (create comparison)
  ↓
OrchestratorService.create_comparison_job()
  ├── Creates Job record
  ├── Creates 4 JobStage records:
  │   ├── OCR (old drawing)
  │   ├── OCR (new drawing)
  │   ├── Diff
  │   └── Summary
  └── Publishes OCR tasks to Pub/Sub
```

### 2. Processing Pipeline Flow

```
OCR Tasks Published to Pub/Sub
  ↓
OCR Workers (GKE pods) consume messages
  ├── Download PDF from GCS
  ├── Convert PDF → PNG (400 DPI)
  ├── Extract text using GPT-4o Vision API
  ├── Save OCR JSON to GCS
  ├── Update JobStage status → 'completed'
  └── Call orchestrator.on_ocr_complete()
  ↓
When BOTH OCR stages complete:
  OrchestratorService.on_ocr_complete()
  └── Publishes diff task to Pub/Sub
  ↓
Diff Worker consumes diff task
  ├── Downloads both PDFs from GCS
  ├── Converts every page to PNG (preserving drawing names)
  ├── Aligns each page pair sequentially using SIFT
  ├── Generates one overlay per page + uploads to GCS
  ├── Saves a DiffResult row for every page with page metadata
  ├── Streams summary tasks per page as soon as each overlay is ready
  └── Marks diff stage complete after the final page finishes
  ↓
Summary Worker consumes summary task
  ├── Downloads diff results
  ├── Generates AI summary
  ├── Saves ChangeSummary to database
  └── Updates JobStage status → 'completed'
  ↓
Job status → 'completed'
```

### 3. Results Display Flow

```
Frontend polls GET /api/v1/jobs/<id>
  ↓
When job.status === 'completed':
  ↓
GET /api/v1/jobs/<id>/results
  ├── Returns DiffResult (overlay image URL)
  ├── Returns ChangeSummary (text)
  └── Returns change list
  ↓
Results Page displays:
  ├── Overlay image (visual diff)
  ├── Summary text (AI-generated)
  └── Change list (structured changes)
```

---

## Technology Stack

### Backend
- **Framework:** Flask 3.1.2 (Python 3.11)
- **Database:** PostgreSQL 17 (Cloud SQL)
- **ORM:** SQLAlchemy 2.0.23
- **Storage:** Google Cloud Storage
- **Messaging:** Google Cloud Pub/Sub
- **AI/ML:** 
  - GPT-4o Vision (OCR - primary, 40-60 sec/page)
  - Gemini 2.5 Pro (Summarization, Chatbot)
- **Authentication:** OAuth 2.0 + JWT
- **Server:** Gunicorn
- **Container:** Docker

### Frontend
- **Framework:** Next.js 14.2.0
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:** Zustand
- **HTTP Client:** Axios
- **Container:** Docker

### Infrastructure
- **Cloud Provider:** Google Cloud Platform
- **Compute:** 
  - Cloud Run (API + Frontend)
  - Google Kubernetes Engine (Workers)
- **Database:** Cloud SQL (PostgreSQL)
- **Storage:** Cloud Storage (GCS)
- **Messaging:** Pub/Sub
- **Container Registry:** Artifact Registry
- **Secrets:** Secret Manager
- **Identity:** Workload Identity

---

## Key Components

### 1. Orchestrator Service
- **File:** `backend/services/orchestrator.py`
- **Purpose:** Manages job lifecycle and stage coordination
- **Key Methods:**
  - `create_comparison_job()` - Creates job and initializes stages
  - `on_ocr_complete()` - Triggers diff stage when OCRs complete
  - `on_diff_complete()` - Triggers summary stage
  - `on_summary_complete()` - Marks job as completed

### 2. Processing Pipelines
- **OCR Pipeline:** `processing/ocr_pipeline.py`
  - PDF → PNG conversion (400 DPI)
  - GPT-4o Vision API for text extraction
  - 180 second timeout
  - Structured JSON output
- **Diff Pipeline:** `processing/diff_pipeline.py`
  - SIFT-based image alignment
  - Change detection algorithm
  - Overlay image generation (PNG + PDF)
  - Requires 28GB memory
- **Summary Pipeline:** `processing/summary_pipeline.py`
  - AI-powered change summarization
  - Structured change list generation

### 3. Workers
- **OCR Worker:** `workers/ocr_worker.py`
  - Consumes OCR tasks from Pub/Sub
  - Processes PDFs through OCR pipeline
  - Updates job stages
  - Memory: 2Gi, CPU: 1000m
- **Diff Worker:** `workers/diff_worker.py`
  - Consumes diff tasks from Pub/Sub
  - Compares drawings using SIFT
  - Generates overlay images
  - Memory: 28Gi, CPU: 2000m
  - Flow control: max 1 message at a time
- **Summary Worker:** `workers/summary_worker.py`
  - Consumes summary tasks from Pub/Sub
  - Generates AI summaries
  - Saves to database
  - Memory: 2Gi, CPU: 500m

### 4. Storage Service
- **File:** `backend/gcp/storage/storage_service.py`
- **Purpose:** Unified storage abstraction (GCS + local fallback)
- **Key Methods:**
  - `upload_drawing()` - Upload PDFs
  - `upload_ocr_result()` - Save OCR JSON
  - `upload_diff_overlay()` - Save overlay images
  - `download_file()` - Retrieve files
- **Features:**
  - Path normalization (strips gs:// prefix)
  - NumpyJSONEncoder for numpy type serialization

### 5. Database Models
- **File:** `backend/gcp/database/models.py`
- **Key Tables:**
  - `Organization`, `User`, `Project`
  - `Drawing`, `DrawingVersion`
  - `Job`, `JobStage`
  - `DiffResult` (with `diff_metadata` column)
  - `ChangeSummary` (with `summary_metadata` column)
  - `ChatConversation`, `ChatMessage`

---

## Deployment Architecture

### Current Deployment (Fully Operational)

1. **Backend API** (Cloud Run)
   - Service: `buildtrace-backend`
   - Region: `us-west2`
   - URL: `https://buildtrace-backend-otllaxbiza-wl.a.run.app`

2. **Frontend** (Cloud Run)
   - Service: `buildtrace-frontend`
   - Region: `us-west2`
   - URL: `https://buildtrace-frontend-136394139608.us-west2.run.app`

3. **Workers** (GKE - ✅ Operational)
   - Cluster: `buildtrace-dev`
   - Region: `us-west2`
   - Namespace: `prod-app`
   - Node Pool: `high-memory-pool` (e2-highmem-4, 32GB RAM)
   - Deployments:
     - `ocr-worker` (1 replica, 2Gi memory)
     - `diff-worker` (1 replica, 28Gi memory)
     - `summary-worker` (1 replica, 2Gi memory)
   - **Status:** ✅ All workers running and processing jobs

### Infrastructure Components

- **Cloud SQL:** `buildtrace-dev:us-west2:buildtrace-dev-db`
- **GCS Buckets:**
  - `buildtrace-dev-input-buildtrace-dev` (uploads)
  - `buildtrace-dev-processed-buildtrace-dev` (results)
- **Pub/Sub Topics:**
  - `buildtrace-dev-ocr-queue`
  - `buildtrace-dev-diff-queue`
  - `buildtrace-dev-summary-queue`
- **Artifact Registry:**
  - `us-west2-docker.pkg.dev/buildtrace-dev/buildtrace-repo`

---

## Authentication Flow

### OAuth 2.0 + JWT

```
1. User clicks "Login with Google"
   ↓
2. Frontend → GET /api/v1/auth/google/login
   ↓
3. Backend returns auth_url (Google OAuth)
   ↓
4. User redirected to Google
   ↓
5. User authorizes
   ↓
6. Google redirects to /api/v1/auth/google/callback
   ↓
7. Backend:
   ├── Exchanges code for user info
   ├── Creates/updates User record
   ├── Generates JWT token
   └── Redirects to frontend with token
   ↓
8. Frontend:
   ├── Extracts token from URL
   ├── Stores in localStorage
   └── Adds to Authorization header for all API requests
```

---

## Data Flow Summary

1. **Upload:** PDFs → GCS → Database records
2. **Job Creation:** Job + 4 JobStages created
3. **OCR Processing:** PDF → per-page PNG → GPT-4o Vision → OCR JSON → GCS
4. **Diff Processing:** PDF pages → PNG → SIFT Alignment (per page) → Overlay → GCS
5. **Summary Processing:** Each DiffResult → AI Analysis → Page summary → Database
6. **Results:** Database → API (per-page diffs array) → Frontend page selector → User

---

## Current Status

### ✅ Completed (Nov 29, 2025)
- Core application development
- Backend API deployment (Cloud Run)
- Frontend deployment (Cloud Run)
- Database setup (Cloud SQL)
- Storage setup (GCS)
- Pub/Sub topics and subscriptions
- Worker code implementation
- Kubernetes manifests created
- **Worker deployment to GKE** ✅
- **End-to-end job processing** ✅
- **All deployment issues resolved** ✅

### 🚧 Current Focus
- Monitoring & alerting setup
- Rate limiting & token refresh
- Chatbot UI polish

### ⏳ Pending
- Monitoring and alerting setup
- Rate limiting implementation
- Frontend chatbot UI

---

## Performance Metrics

### OCR Processing (GPT-4o)
| Metric | Value |
|--------|-------|
| Time per page | 40-60 seconds |
| Reliability | High (no timeouts) |
| Sections extracted | 18-20 per page |

### Diff Processing (SIFT)
| Metric | Value |
|--------|-------|
| Memory required | 28GB |
| Processing time | 2-3 minutes |
| Keypoints matched | 1500-2000 |

### Comparison: GPT-5 vs GPT-4o
| Metric | GPT-5 | GPT-4o |
|--------|-------|--------|
| Time per page | 85-100+ sec | 40-60 sec |
| Reliability | Frequent timeouts | Stable |
| Total OCR (3 pages) | 9+ min | ~2.5 min |

---

## Next Steps

1. **Immediate:** Fix frontend recent comparisons display
2. **Short-term:** Add monitoring and alerting
3. **Medium-term:** Implement rate limiting
4. **Long-term:** Feature enhancements (see PENDING.md)

---

**For detailed information, see:**
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture details
- [PROGRESS.md](./PROGRESS.md) - Implementation status
- [PENDING.md](./PENDING.md) - Remaining tasks

