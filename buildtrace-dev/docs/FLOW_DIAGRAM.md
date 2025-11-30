# BuildTrace Data Flow Diagrams

**Last Updated:** November 29, 2025

---

## 1. Complete User Flow

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       │ 1. Navigate to Frontend
       ▼
┌─────────────────────────────────────┐
│  Frontend (Next.js)                 │
│  https://buildtrace-frontend-...    │
└──────┬──────────────────────────────┘
       │
       │ 2. Click "Login with Google"
       ▼
┌─────────────────────────────────────┐
│  GET /api/v1/auth/google/login      │
│  → Backend (Cloud Run)              │
└──────┬──────────────────────────────┘
       │
       │ 3. Returns auth_url
       ▼
┌─────────────────────────────────────┐
│  Google OAuth                       │
│  User authorizes                    │
└──────┬──────────────────────────────┘
       │
       │ 4. Redirect with code
       ▼
┌─────────────────────────────────────┐
│  GET /api/v1/auth/google/callback   │
│  → Backend                          │
│  ├── Exchanges code for user info   │
│  ├── Creates/updates User record   │
│  ├── Generates JWT token            │
│  └── Redirects to frontend + token  │
└──────┬──────────────────────────────┘
       │
       │ 5. Frontend stores token
       ▼
┌─────────────────────────────────────┐
│  Upload Page                        │
│  User uploads 2 PDFs                │
└──────┬──────────────────────────────┘
       │
       │ 6. POST /api/v1/drawings/upload (old)
       ▼
┌─────────────────────────────────────┐
│  DrawingUploadService               │
│  ├── Validates file                 │
│  ├── Uploads to GCS                 │
│  ├── Creates DrawingVersion         │
│  └── Returns drawing_version_id_1   │
└──────┬──────────────────────────────┘
       │
       │ 7. POST /api/v1/drawings/upload (new)
       ▼
┌─────────────────────────────────────┐
│  DrawingUploadService               │
│  (same process)                     │
│  Returns drawing_version_id_2        │
└──────┬──────────────────────────────┘
       │
       │ 8. POST /api/v1/jobs
       ▼
┌─────────────────────────────────────┐
│  OrchestratorService                │
│  create_comparison_job()            │
│  ├── Creates Job record             │
│  ├── Creates 4 JobStage records     │
│  └── Publishes OCR tasks to Pub/Sub  │
└──────┬──────────────────────────────┘
       │
       │ 9. Frontend polls job status
       ▼
┌─────────────────────────────────────┐
│  GET /api/v1/jobs/<id>              │
│  (Polling every 2 seconds)          │
└──────┬──────────────────────────────┘
       │
       │ 10. When job.status === 'completed'
       ▼
┌─────────────────────────────────────┐
│  GET /api/v1/jobs/<id>/results      │
│  Returns:                            │
│  ├── DiffResult (overlay image)      │
│  ├── ChangeSummary (text)            │
│  └── Change list                    │
└──────┬──────────────────────────────┘
       │
       │ 11. Display results
       ▼
┌─────────────────────────────────────┐
│  Results Page                       │
│  ├── Overlay image                  │
│  ├── Summary text                   │
│  └── Change list                    │
└─────────────────────────────────────┘
```

---

## 2. Job Processing Flow

```
┌─────────────────────────────────────┐
│  OrchestratorService                │
│  create_comparison_job()            │
└──────┬──────────────────────────────┘
       │
       │ Creates Job + 4 JobStages
       │
       │ Publishes OCR tasks to Pub/Sub
       ▼
┌─────────────────────────────────────┐
│  Pub/Sub Topic:                     │
│  buildtrace-dev-ocr-queue            │
└──────┬──────────────────────────────┘
       │
       │ OCR Worker subscribes
       ▼
┌─────────────────────────────────────┐
│  OCR Worker (GKE Pod)               │
│  ├── Consumes message                │
│  ├── Downloads PDF from GCS          │
│  ├── Converts PDF → PNG (400 DPI)   │
│  ├── Calls Gemini Vision API         │
│  ├── Extracts text + layout          │
│  ├── Saves OCR JSON to GCS           │
│  ├── Updates JobStage → 'completed' │
│  └── Calls orchestrator.on_ocr_complete()
└──────┬──────────────────────────────┘
       │
       │ When BOTH OCR stages complete
       ▼
┌─────────────────────────────────────┐
│  OrchestratorService                │
│  on_ocr_complete()                  │
│  └── Publishes diff task to Pub/Sub │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Pub/Sub Topic:                     │
│  buildtrace-dev-diff-queue           │
└──────┬──────────────────────────────┘
       │
       │ Diff Worker subscribes
       ▼
┌─────────────────────────────────────┐
│  Diff Worker (GKE Pod)              │
│  ├── Consumes message                │
│  ├── Downloads both OCR JSONs       │
│  ├── Aligns images (SIFT)            │
│  ├── Calculates differences          │
│  ├── Generates overlay image         │
│  ├── Saves DiffResult to DB         │
│  ├── Uploads overlay to GCS          │
│  ├── Updates JobStage → 'completed' │
│  └── Calls orchestrator.on_diff_complete()
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  OrchestratorService                │
│  on_diff_complete()                 │
│  └── Publishes summary task         │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Pub/Sub Topic:                     │
│  buildtrace-dev-summary-queue        │
└──────┬──────────────────────────────┘
       │
       │ Summary Worker subscribes
       ▼
┌─────────────────────────────────────┐
│  Summary Worker (GKE Pod)           │
│  ├── Consumes message                │
│  ├── Downloads diff results          │
│  ├── Calls Gemini/GPT for summary    │
│  ├── Generates structured summary    │
│  ├── Saves ChangeSummary to DB       │
│  ├── Updates JobStage → 'completed' │
│  └── Calls orchestrator.on_summary_complete()
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  OrchestratorService                │
│  on_summary_complete()              │
│  └── Updates Job.status → 'completed'
└─────────────────────────────────────┘
```

---

## 3. Data Storage Flow

```
┌─────────────────────────────────────┐
│  User Uploads PDF                   │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  DrawingUploadService               │
│  upload_drawing()                  │
└──────┬──────────────────────────────┘
       │
       │ Uploads to GCS
       ▼
┌─────────────────────────────────────┐
│  GCS Bucket:                         │
│  buildtrace-dev-input-...           │
│  └── drawings/<project>/<version>/  │
│      └── <filename>.pdf             │
└──────┬──────────────────────────────┘
       │
       │ Creates database record
       ▼
┌─────────────────────────────────────┐
│  Cloud SQL (PostgreSQL)              │
│  ├── DrawingVersion record           │
│  └── Links to GCS path              │
└──────┬──────────────────────────────┘
       │
       │ OCR Worker processes
       ▼
┌─────────────────────────────────────┐
│  OCR Pipeline                       │
│  ├── Downloads PDF from GCS          │
│  ├── Converts to PNG                 │
│  └── Extracts text                   │
└──────┬──────────────────────────────┘
       │
       │ Saves OCR results
       ▼
┌─────────────────────────────────────┐
│  GCS Bucket:                         │
│  buildtrace-dev-processed-...         │
│  └── ocr/<job_id>/<version>/        │
│      └── ocr_result.json             │
└──────┬──────────────────────────────┘
       │
       │ Diff Worker processes
       ▼
┌─────────────────────────────────────┐
│  Diff Pipeline                      │
│  ├── Downloads OCR JSONs             │
│  ├── Aligns images                   │
│  └── Generates overlay               │
└──────┬──────────────────────────────┘
       │
       │ Saves diff results
       ▼
┌─────────────────────────────────────┐
│  Cloud SQL:                          │
│  └── DiffResult record               │
│      └── overlay_image_path         │
│                                      │
│  GCS Bucket:                         │
│  └── overlays/<job_id>/              │
│      └── overlay.png                 │
└──────┬──────────────────────────────┘
       │
       │ Summary Worker processes
       ▼
┌─────────────────────────────────────┐
│  Summary Pipeline                   │
│  ├── Downloads diff results          │
│  └── Generates AI summary            │
└──────┬──────────────────────────────┘
       │
       │ Saves summary
       ▼
┌─────────────────────────────────────┐
│  Cloud SQL:                          │
│  └── ChangeSummary record            │
│      ├── summary_text                │
│      └── change_list (JSON)          │
└─────────────────────────────────────┘
```

---

## 4. Authentication Flow

```
┌─────────────────────────────────────┐
│  User clicks "Login with Google"    │
└──────┬──────────────────────────────┘
       │
       │ GET /api/v1/auth/google/login
       ▼
┌─────────────────────────────────────┐
│  Backend generates auth_url          │
│  (Google OAuth URL)                 │
└──────┬──────────────────────────────┘
       │
       │ Redirect to Google
       ▼
┌─────────────────────────────────────┐
│  Google OAuth                       │
│  User authorizes                    │
└──────┬──────────────────────────────┘
       │
       │ Redirect with code
       ▼
┌─────────────────────────────────────┐
│  GET /api/v1/auth/google/callback   │
│  ?code=...                          │
└──────┬──────────────────────────────┘
       │
       │ Backend:
       │ 1. Exchanges code for token
       │ 2. Gets user info from Google
       │ 3. Creates/updates User record
       │ 4. Generates JWT token
       │ 5. Sets session cookie
       ▼
┌─────────────────────────────────────┐
│  Redirect to Frontend               │
│  ?token=<jwt_token>                  │
└──────┬──────────────────────────────┘
       │
       │ Frontend:
       │ 1. Extracts token from URL
       │ 2. Stores in localStorage
       │ 3. Adds to Authorization header
       ▼
┌─────────────────────────────────────┐
│  All API requests include:          │
│  Authorization: Bearer <token>        │
└─────────────────────────────────────┘
```

---

## 5. Worker Deployment Architecture

```
┌─────────────────────────────────────┐
│  GKE Cluster: buildtrace-dev        │
│  Region: us-west2                   │
│  Namespace: prod-app                │
└──────┬──────────────────────────────┘
       │
       ├─── OCR Worker Deployment
       │    ├── Replicas: 2
       │    ├── Image: buildtrace-backend:latest
       │    ├── Command: python3 backend/workers/ocr_worker_entry.py
       │    ├── ServiceAccount: buildtrace-app-sa
       │    └── Resources: 2Gi memory, 1000m CPU
       │
       ├─── Diff Worker Deployment
       │    ├── Replicas: 2
       │    ├── Image: buildtrace-backend:latest
       │    ├── Command: python3 backend/workers/diff_worker_entry.py
       │    ├── ServiceAccount: buildtrace-app-sa
       │    └── Resources: 2Gi memory, 1000m CPU
       │
       └─── Summary Worker Deployment
            ├── Replicas: 2
            ├── Image: buildtrace-backend:latest
            ├── Command: python3 backend/workers/summary_worker_entry.py
            ├── ServiceAccount: buildtrace-app-sa
            └── Resources: 2Gi memory, 1000m CPU

┌─────────────────────────────────────┐
│  Service Account: buildtrace-app-sa │
│  Workload Identity:                 │
│  buildtrace-gke-workload@...        │
│  Permissions:                       │
│  ├── roles/pubsub.subscriber        │
│  ├── roles/storage.objectAdmin       │
│  ├── roles/secretmanager.secretAccessor
│  └── roles/cloudsql.client          │
└─────────────────────────────────────┘
```

---

## 6. Error Handling Flow

```
┌─────────────────────────────────────┐
│  Worker Processing Task            │
└──────┬──────────────────────────────┘
       │
       │ Error occurs
       ▼
┌─────────────────────────────────────┐
│  Worker catches exception            │
│  ├── Logs error                     │
│  ├── Updates JobStage.status        │
│  │   → 'failed'                     │
│  └── Updates JobStage.error_message │
└──────┬──────────────────────────────┘
       │
       │ NACK message (if Pub/Sub)
       ▼
┌─────────────────────────────────────┐
│  Pub/Sub redelivers message         │
│  (up to max delivery attempts)      │
└──────┬──────────────────────────────┘
       │
       │ If all retries fail
       ▼
┌─────────────────────────────────────┐
│  JobStage.status = 'failed'         │
│  Job.status = 'failed'               │
└──────┬──────────────────────────────┘
       │
       │ Frontend polls job status
       ▼
┌─────────────────────────────────────┐
│  Frontend displays error message    │
│  User can retry or cancel           │
└─────────────────────────────────────┘
```

---

## 7. Chatbot Flow

```
┌─────────────────────────────────────┐
│  User asks question in chatbot      │
└──────┬──────────────────────────────┘
       │
       │ POST /api/v1/chat/message
       │ { conversation_id, message, drawing_version_ids }
       ▼
┌─────────────────────────────────────┐
│  ChatbotService                     │
│  ├── ContextRetriever               │
│  │   ├── Downloads OCR JSONs        │
│  │   └── Extracts context            │
│  ├── Formats prompt with context    │
│  ├── Calls Gemini 2.5 Pro          │
│  └── Returns response               │
└──────┬──────────────────────────────┘
       │
       │ Saves to database
       ▼
┌─────────────────────────────────────┐
│  Cloud SQL:                         │
│  ├── ChatConversation record        │
│  └── ChatMessage record              │
└──────┬──────────────────────────────┘
       │
       │ Returns response
       ▼
┌─────────────────────────────────────┐
│  Frontend displays response         │
└─────────────────────────────────────┘
```

---

**For system architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)**  
**For implementation status, see [PROGRESS.md](./PROGRESS.md)**

