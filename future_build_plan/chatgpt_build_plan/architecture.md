# BuildTrace Architecture (Code-Aware)

_Last updated: 2025-11-18_

This revision ties the high-level plan back to the concrete code that exists in the repo today (`buildtrace-overlay-` for the Python/Flask backend and `buildtrace-overlay-/frontend` for the Next.js client). Use it while iterating on the next product version and when aligning upcoming UI work with the attached screenshots.

---

## 0. Source Layout & Responsibilities

| Path | Stack | Notes |
| --- | --- | --- |
| `buildtrace-overlay-/app.py` | Flask monolith | All HTTP endpoints, file workflows, and blueprint registration live here. |
| `buildtrace-overlay-/chunked_processor.py`, `complete_drawing_pipeline.py` | Python + OpenCV/PyMuPDF/OpenAI | The heavy drawing comparison + AI analysis logic. |
| `buildtrace-overlay-/gcp/*` | Infra helpers | Database ORM, storage wrapper, Cloud Tasks orchestration, background worker (`infrastructure/job_processor.py`). |
| `buildtrace-overlay-/frontend` | Next.js App Router, Tailwind, Zustand | Upload, progress, and results flows wired to the Flask endpoints. |
| `buildtrace-overlay-/templates`, `static/js` | Legacy Flask-rendered UI | Useful reference but superseded by the Next.js client. |

---

## 1. Runtime & Request Flow

1. **Auth gating (client-only for now):** `src/app/page.tsx` defers rendering of the upload flow until `useAuthStore` confirms a user session. The store still expects `/auth/*` endpoints, which do not exist yet on the Flask side, so bridging those routes (or swapping to Supabase/Firebase) is a key next step.
2. **File upload:** `UploadPage.tsx` pairs two files, calls `apiClient.submitComparison('/upload')`, and then triggers `/process/<session_id>` to launch server-side processing.
3. **Processing pipeline:** Flask saves files to Cloud Storage (or local), records metadata (`Session`, `Drawing` rows), then either processes synchronously via `chunked_process_documents` or schedules work through Cloud Tasks / `JobProcessor`.
4. **Results delivery:** The front-end fetches `/api/drawings/<session_id>` for overlay imagery and `/api/changes/<session_id>` for AI-generated change lists, rendering them in `ResultsPage.tsx` along with chat/summary widgets.
5. **Session summaries:** Secondary endpoints like `/api/session/<session_id>/summary` (Blueprint in `session_summary_api.py`) aggregate granular analysis into dashboards.

---

## 2. Frontend Implementation (Next.js)

- **App Router & providers:** `frontend/src/app` drives routing; `components/providers/Providers.tsx` wires up global context (theme, toasts, etc.).
- **State & API client:** A persisted Zustand store (`store/authStore.ts`) tracks auth flags and delegates network calls to a shared Axios wrapper.

```
1:34:buildtrace-overlay-/frontend/src/lib/api.ts
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://buildtrace-overlay-lioa4ql2nq-uc.a.run.app',
      timeout: 60000,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true
    })
```

- **Upload UX:** `components/upload/*` encapsulates drag-and-drop, progress indicators, recent session cards, and CTA buttons. The UX mirrors the screenshot expectations (two-card layout, multi-step progress rail).
- **Results UX:** `components/results/*` renders the overlay viewer, sortable change list, and chat assistant. `ResultsPage.tsx` coordinates API calls and selection state.
- **Chat assistant placeholder:** `ChatAssistant` currently posts to `/api/chat`; ensure backend chat endpoints remain compatible or replace with a Supabase Edge function.

---

## 3. Backend Implementation (Flask + AI Pipeline)

### 3.1 Application Layer (`app.py`)
- Routes handle:
  - Health and diagnostics (`/health`, `/api/session/<id>/diagnostics`).
  - File ingest (`/upload`, `/api/upload-urls`, `/api/process-uploaded-files`).
  - Job control (`/process/<id>`, `/api/session/<id>/retry`, `/api/session/<id>/cleanup-duplicates`).
  - Data retrieval (`/api/drawings/<id>`, `/api/changes/<id>`, `/api/sessions/recent`).
  - Chat APIs (`/api/chat/<session_id>` trio).
  - Cloud Task webhooks (`/api/process-task`, `/api/retry-task`).

```
523:720:buildtrace-overlay-/app.py
@app.route('/upload', methods=['POST'])
def upload_files():
    # Validates files, creates a Session row, stores PDFs via storage_service,
    # and inserts Drawing records before returning the generated session_id.
    ...
```

- Persistence toggles between DB-backed and local JSON fallbacks based on `config.USE_DATABASE`.
- Direct-to-GCS uploads rely on `storage_service.generate_signed_upload_url`, which falls back to the `/api/upload-direct/<path>` endpoint when running on Cloud Run without signing keys.

### 3.2 Processing Layer

- `chunked_processor.ChunkedProcessor` decides whether to run synchronously (≤ `max_sync_pages`) or degrade to lightweight processing. It extracts drawing names, aligns overlays, and invokes OpenAI for textual summaries.

```
33:142:buildtrace-overlay-/chunked_processor.py
class ChunkedProcessor:
    def __init__(...):
        ...
    def should_process_sync(...):
        ...
    def process_sync(...):
        # Converts PDFs to page images, matches drawings, runs AI analysis per overlay,
        # and writes structured results to JSON for the frontend.
```

- `complete_drawing_pipeline` remains the CLI-friendly wrapper for batch conversions and AI analysis, invoked by the background worker for larger jobs.
- `gcp/infrastructure/job_processor.py` polls the `ProcessingJob` table, downloads PDFs from storage, runs `complete_drawing_pipeline`, and persists `Comparison` + `AnalysisResult` rows. This keeps Cloud Run request handlers lightweight.
- `gcp/tasks/task_processor.py` encapsulates Cloud Tasks queue management for truly asynchronous dispatch (used when `config.USE_ASYNC_PROCESSING` is toggled on).

---

## 4. Data & Storage

- **ORM Models:** SQLAlchemy models live in `gcp/database/models.py`. Core tables include `User`, `Project`, `Session`, `Drawing`, `Comparison`, `AnalysisResult`, `ChatConversation`, and `ProcessingJob`. Manual overlays/summaries from the earlier high-level plan map to `Comparison` + `AnalysisResult` records today; future iterations should extend the existing schema rather than invent new tables.

```
151:200:buildtrace-overlay-/gcp/database/models.py
class Comparison(Base):
    __tablename__ = 'comparisons'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    old_drawing_id = Column(String(36), ForeignKey('drawings.id'), nullable=False)
    new_drawing_id = Column(String(36), ForeignKey('drawings.id'), nullable=False)
    drawing_name = Column(String(100), nullable=False)
    overlay_path = Column(Text)
    ...
class AnalysisResult(Base):
    __tablename__ = 'analysis_results'
    comparison_id = Column(String(36), ForeignKey('comparisons.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    changes_found = Column(JSON)
    analysis_summary = Column(Text)
```

- **Storage abstraction:** `gcp/storage/storage_service.py` hides GCS vs local storage differences, exposing `upload_file`, `download_to_filename`, `generate_signed_url`, etc., used throughout `app.py`.

```
61:92:buildtrace-overlay-/gcp/storage/storage_service.py
def upload_file(self, file_content, destination_path, content_type=None):
    if not self.bucket:
        return self._save_local_file(file_content, destination_path)
    blob = self.bucket.blob(destination_path)
    ...
    blob.upload_from_file(file_content, rewind=True)
    return f"gs://{self.bucket_name}/{destination_path}"
```

---

## 5. Deployment & Ops

- **Config toggles:** `config.py` centralizes feature flags (DB, GCS, async processing, Firebase Auth). Ensure CI/CD populates `.env` or Secret Manager with DB credentials, bucket names, and OpenAI keys before shipping.
- **Containerization:** Both `buildtrace-overlay-/Dockerfile` and `gcp/deployment/Dockerfile.full` target Cloud Run/GKE. Frontend has its own Next.js build pipeline (`frontend/setup.sh`, `package.json` scripts).
- **Job orchestration:** Cloud Tasks + background worker allow long-running comparisons to outlive HTTP timeouts. For GKE adoption, consider migrating `JobProcessor` into a dedicated Deployment with autoscaling.
- **Observability:** Logging is already structured via Python’s logging module; metrics hooks still need to be added (Prometheus exporters or Cloud Monitoring custom metrics).

---

## 6. Gaps & Planned Improvements

1. **Auth parity:** Frontend expects `/auth/login`, `/auth/signup`, `/auth/me`, `/auth/logout`, `/auth/google`, but `app.py` lacks matching endpoints. Decide between enabling `app_with_auth.py` (which integrates Flask-Login/Firebase) or pointing the client at Supabase Auth.
2. **Manual overlay persistence:** Current DB schema stores only AI-generated overlays; the new UX’s manual edit tooling should extend `Comparison`/`AnalysisResult` or add a `manual_overlays` table consistent with the earlier architecture note.
3. **Realtime job status:** `UploadPage` simulates progress locally. Add polling or server-sent events that hit `/api/session/<id>/status` (already present) to display true pipeline state.
4. **Results viewer assets:** `/api/drawings/<id>` currently returns signed URLs pointing to Cloud Storage. Confirm the Next.js results page can read those (CORS, expiration) and fall back to `download/<session_id>/<filename>` for local dev.
5. **Chat assistant:** The front-end depends on `/api/chat/<session_id>` endpoints; ensure rate limiting, context window management, and audit logging before exposing to users.
6. **Screenshot alignment:** Once the new UI spec is finalized, map each major section (upload cards, progress rail, results inspector) to the existing components to minimize rework.

---

## 7. Next Steps

1. Wire up functional auth endpoints (either in Flask or via an external provider) so `useAuthStore` succeeds.
2. Enable async processing by deploying `gcp/infrastructure/job_processor.py` as a background worker and pointing `/process/<id>` to enqueue jobs instead of doing everything inline.
3. Finalize the data contract for overlays/changes so both `/api/drawings/*` and `/api/changes/*` match what the Next.js results widgets expect.
4. Add integration tests that exercise the upload → process → results flow end-to-end, using the CLI pipeline for deterministic fixtures.

