# BuildTrace Architecture (GKE)

_Last updated: 2025-11-17_

This document describes the **high-level architecture** for BuildTrace running on **Google Kubernetes Engine (GKE)**.

It is intentionally implementation-agnostic:  
- ✅ Focuses on **components, data flows, and responsibilities**  

You’ll wire in concrete services (queues, infra config, charts, etc.) over the week.

---

## 1. Goals & Constraints

**Product goal:**  
Detect and summarize changes between versions of construction drawings, with a feedback loop where humans can correct overlays and summaries.

**Architecture goals:**

- Scalable: handle many drawings and heavy OCR/diff workloads.
- Async: user doesn’t wait for heavy processing in the request cycle.
- Modular: front-end, API, orchestrator, workers, and storage are cleanly separated.
- Observable: clear metrics around jobs, latency, and failure rates.
- Secure: proper key handling, limited network exposure, and per-tenant isolation at the app layer.

---

## 2. High-Level Component Map

At a high level, the system consists of:

1. **Client Applications**
   - Web app for:
     - Uploading drawings
     - Viewing diffs & summaries
     - Manually editing overlays / summaries

2. **Edge & API Layer (GKE)**
   - HTTP(S) Load Balancer + GKE Ingress
   - API service(s) for:
     - Auth integration
     - Project & drawing management
     - Job creation & status queries

3. **Async Processing Layer (GKE)**
   - Orchestrator service (control plane)
   - Worker services:
     - OCR worker
     - Diff worker
     - Summary (LLM) worker

4. **Data & Storage**
   - Relational DB (e.g., Cloud SQL for Postgres)
   - Object storage (e.g., GCS buckets) for drawings & artifacts
   - Metrics and dashboards

5. **Platform / Operations**
   - CI/CD (GitHub Actions)
   - Monitoring & alerting (Prometheus/Grafana)
   - Secret management

---

## 3. GKE Cluster Layout

### 3.1 Cluster

- Single regional GKE cluster (e.g., `buildtrace-prod`)
- Namespaces (example):
  - `prod-app`: app services (API, workers, web)
  - `prod-observability`: Prometheus, Grafana, etc.
  - `prod-infra`: internal supporting tooling

### 3.2 Node Pools

- **`web-standard` node pool**
  - API services
  - Web frontend (if containerized)
  - Orchestrator

- **`workers-cpu` node pool**
  - OCR workers
  - Diff workers
  - Summary workers

- **(optional, later) `workers-gpu` node pool**
  - GPU-based OCR / VLM models if needed.

Autoscaling is configured per Deployment so each pool can scale independently based on CPU/memory/utilization metrics.

---

## 4. Edge, Auth, and API

### 4.1 Ingress & Routing

- **External HTTP(S) Load Balancer** terminates TLS.
- **GKE Ingress** routes traffic by host/path:
  - `app.buildtrace.ai` → Web frontend service
  - `api.buildtrace.ai` → API service

### 4.2 Authentication

- Authentication handled by a managed auth provider (e.g., Supabase Auth or similar).
- Flow:
  1. User logs in via frontend using provider’s SDK.
  2. Provider returns an access token (e.g., JWT).
  3. Frontend includes token in API calls.
  4. API validates token using provider’s public keys.
  5. Tenant/role-based authorization enforced at the application level:
     - Which projects a user can access
     - Permissions to modify overlays, approve summaries, etc.

### 4.3 API Service Responsibilities

The **API service** (e.g., FastAPI/Express) provides:

- **Project & tenant management**
  - Organizations, projects, roles
- **Drawing lifecycle**
  - Upload endpoints
  - Linking versions of the same drawing
- **Job initiation**
  - When a file is uploaded, API creates a logical “processing job”
- **Job status read**
  - Return current status of OCR/diff/summary for a drawing version
- **Overlay and summary updates**
  - Endpoints for manual edits to overlays and text summaries

The API never directly performs heavy OCR or diff logic; it initiates **async jobs** and tracks them via the DB.

---

## 5. Async Processing Architecture

The async processing is split into:

1. **Orchestrator**
2. **Specialized Workers**

> Note: The specific queueing mechanism is intentionally left abstract here.  
> We assume an internal **Job Queue** system with:
> - A way to enqueue tasks
> - One or more worker services subscribing to those tasks
> - At-least-once execution semantics

### 5.1 Orchestrator Service

**Responsibilities:**

- Watches for new **drawings** or **new versions** registered by the API.
- Breaks down work into **stages**:
  1. OCR
  2. Normalization/vectorization
  3. Diff
  4. Summary generation
- Enqueues stage-specific tasks into the Job Queue.
- Updates job state in the DB:
  - `created`, `in_progress`, `completed`, `failed`
  - Sub-status per stage (ocr/diff/summary)
- Ensures idempotency & retry safety for job transitions.

### 5.2 Worker Services (per stage)

Each worker runs as a **Deployment** in GKE with horizontal autoscaling.

#### 5.2.1 OCR Worker

- **Input:** Job reference + drawing version ID.
- **Steps:**
  1. Download drawing (PDF/image) from object storage.
  2. Run OCR pipeline (text + layout extraction).
  3. Produce structured output:
     - Raw text
     - Bounding boxes
     - Detected symbols/annotations
  4. Store:
     - Structured OCR JSON in object storage
     - Metadata row in DB
  5. Mark OCR stage as `completed` or `failed`.

#### 5.2.2 Diff Worker

- **Input:** Job reference + pair of drawing version IDs (old/new).
- **Steps:**
  1. Read OCR/normalized representations for both versions.
  2. Compare geometry, text, and annotations.
  3. Produce a **normalized diff structure**:
     - Added / removed / changed elements
     - Regions with changes (bounding boxes)
  4. Store diff JSON in object storage + DB reference.
  5. Mark diff stage as `completed` or `failed`.

#### 5.2.3 Summary Worker

- **Input:** Job reference + diff ID.
- **Steps:**
  1. Load diff JSON.
  2. Call LLM(s) with a well-defined prompt:
     - Generate human-readable change summary.
     - Generate bullet points and risk-oriented highlights.
  3. Store:
     - Summary text
     - Metadata (prompt, model, version, etc.)
  4. Mark summary stage as `completed` or `failed`.

---

## 6. Manual Overlay & Human-in-the-Loop Edits

Manual corrections are a core workflow and should be treated as **first-class entities**.

### 6.1 UI Behavior

- The frontend loads the drawing + diff overlay:
  - Underlay: rasterized drawing.
  - Overlay: bounding boxes and annotations from diff JSON.
- Users can:
  - Add, remove, or move regions.
  - Tag change types (e.g., “dimension change”, “scope addition”).

### 6.2 Data Model

In the database:

- `diff_results`
  - `id`, `drawing_version_old_id`, `drawing_version_new_id`
  - `machine_generated_overlay_ref` (object storage path)
  - `created_at`, `created_by` (system)

- `manual_overlays`
  - `id`, `diff_result_id`
  - `overlay_ref` (object storage path)
  - `created_by` (user)
  - `is_active` flag
  - `created_at`, `updated_at`

- `change_summaries`
  - `id`, `diff_result_id`
  - `summary_text`
  - `source` (`machine`, `human_corrected`)
  - `created_by`
  - `created_at`, `updated_at`

### 6.3 Regenerate Summary Flow

- User edits the overlay and clicks “Regenerate Summary”:
  1. Frontend sends updated overlay definition to API.
  2. API stores new `manual_overlay` and triggers a **new summary job**.
  3. Orchestrator enqueues a summary task referencing the latest overlay.
  4. Summary worker uses the updated diff/overlay JSON.
  5. New `change_summaries` row is created with source `human_corrected`.

---

## 7. Data & Storage

### 7.1 Relational Database

Use a managed relational engine (e.g., Postgres) for:

- Tenancy & auth metadata (organization, users, roles)
- Projects and drawing versioning
- Job & stage statuses
- References to object storage artifacts
- Audit logs (who viewed/changed what)

Key tables (high level):

- `organizations`
- `users`
- `projects`
- `drawings`
- `drawing_versions`
- `jobs`
- `job_stages` (ocr/diff/summary state)
- `diff_results`
- `manual_overlays`
- `change_summaries`
- `audit_logs`

### 7.2 Object Storage

Use object storage (e.g., GCS buckets) for:

- Raw uploads (PDF/DWG/images)
- Rasterized images per page/layer
- OCR JSON outputs
- Diff JSON outputs
- Overlay JSON (machine + manual)
- Any binary artifacts (thumbnails, exports)

Bucket examples:

- `buildtrace-prod-drawings-raw`
- `buildtrace-prod-drawings-processed`
- `buildtrace-prod-diff-artifacts`
- `buildtrace-prod-logs` (optional)

Objects should be referenced via **IDs in the DB**, not raw URLs.

---

## 8. Observability & Metrics

### 8.1 Metrics (Prometheus + Grafana)

Expose app-level metrics such as:

- Number of drawings uploaded per day
- Queue depth / pending jobs per stage (as custom metrics)
- Time from:
  - upload → OCR complete
  - OCR complete → diff complete
  - diff complete → summary complete
- Error rates per stage and per tenant

These metrics are visualized via Grafana dashboards:

- “System health” dashboard
- “Per-tenant usage” dashboard
- “Worker performance” dashboard (CPU, memory, throughput)

### 8.2 Logging

- Structured logs from all services (API, orchestrator, workers).
- Include:
  - Job IDs
  - Tenant IDs
  - Stage and status
- Use log-based metrics and/or alerts for:
  - Frequent OCR failures
  - Diff calculation failures
  - LLM errors or rate limits

---

## 9. CI/CD

### 9.1 Source Layout (example)

- `/services/api`
- `/services/orchestrator`
- `/services/worker-ocr`
- `/services/worker-diff`
- `/services/worker-summary`
- `/webapp`
- `/documentation`

### 9.2 Pipeline Outline (GitHub Actions)

For each service:

1. Run tests (unit + integration if available).
2. Build container image.
3. Push image to container registry.
4. Update deployment manifests/configs via:
   - GitOps (e.g., ArgoCD) **or**
   - Direct `kubectl`/`gcloud` apply from CI.

Rollouts should be:

- Incremental (rolling updates)
- Observable (track error rate & latency post-deploy)
- Easily reversible (revert to previous image tag)

---

## 10. Security & Secrets

### 10.1 Secret Management

- API keys (LLM providers, auth providers)
- DB credentials (or use managed IAM auth when available)
- Any signing keys used for internal tokens

These should be stored in a secure secret store and made available to pods via:

- Environment variables OR
- Mounted secret files (via CSI driver)

### 10.2 Network & Access

- Limit DB access to the GKE cluster network (private IP / VPC).
- Restrict public exposure to:
  - Web frontend
  - API endpoints behind auth.
- Implement RBAC and namespace-level separation within the cluster for operational safety.

---

## 11. Key Flows (End-to-End)

### 11.1 Drawing Upload & Processing

1. User uploads drawing via frontend.
2. Frontend calls API with file and metadata.
3. API:
   - Stores file in object storage.
   - Inserts `drawing` and `drawing_version` entries.
   - Inserts `job` entry with initial stage `ocr`.
4. Orchestrator sees new job/stage and enqueues OCR task.
5. OCR worker processes, stores OCR output, updates job stage → `ocr_completed`, next stage `diff`.
6. Orchestrator enqueues diff task.
7. Diff worker processes, stores diff output, updates job stage → `diff_completed`, next stage `summary`.
8. Orchestrator enqueues summary task.
9. Summary worker generates description, stores summary, marks job → `completed`.
10. Frontend polls or uses websockets/SSE to update UI and display results.

### 11.2 Manual Correction & Resummary

1. User reviews overlay and summary in UI.
2. User adjusts overlay (add/remove/move regions).
3. Frontend sends updated overlay to API.
4. API stores new `manual_overlay` and creates a new summary stage for that diff.
5. Orchestrator enqueues a new summary task with a reference to the manual overlay.
6. Summary worker generates a revised summary and marks it as `human_corrected`.
7. UI shows updated summary and indicates it is based on manual corrections.

---

## 12. Next Steps

Over the coming week, you can:

- Choose and integrate a concrete **Job Queue** implementation.
- Flesh out:
  - Detailed DB schema
  - Service boundaries and API contracts
- Add diagrams (sequence diagrams, component diagrams) into this file.

This document should remain the canonical high-level reference for anyone joining as a new engineer.

