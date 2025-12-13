# BuildTrace Streaming Pipeline

## Overview

The streaming pipeline enables real-time, incremental processing of multi-page PDF comparisons. Instead of waiting for all pages to complete before showing results, users see each page's results as soon as they're ready.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         STREAMING PIPELINE FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

Upload PDF (3 pages)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  PAGE EXTRACTION                                                                 │
│  - PDFs stored in GCS immediately                                               │
│  - Each page extracted to individual PNG files                                  │
│  - Per-page job stages created                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼ (parallel page processing)

TIME ─────────────────────────────────────────────────────────────────────────────▶

t=0    ┌──────────────────────────────────────────────────────────────────────────┐
       │ PAGE 1                                                                    │
       │ OCR → DISPLAY → Diff → DISPLAY OVERLAY → Summary → DISPLAY AI SUMMARY   │
       └──────────────────────────────────────────────────────────────────────────┘
               │
t=5s           │  ┌──────────────────────────────────────────────────────────────┐
               │  │ PAGE 2                                                        │
               │  │ OCR → DISPLAY → Diff → DISPLAY OVERLAY → Summary → DISPLAY   │
               │  └──────────────────────────────────────────────────────────────┘
               │          │
t=10s          │          │  ┌───────────────────────────────────────────────────┐
               │          │  │ PAGE 3                                             │
               │          │  │ OCR → DISPLAY → Diff → DISPLAY → Summary → DONE   │
               │          │  └───────────────────────────────────────────────────┘
```

## Key Components

### 1. Page Extractor Service
**File:** `backend/services/page_extractor.py`

Extracts individual pages from PDFs and uploads them to GCS:
- Downloads PDF from GCS
- Extracts drawing names using OCR
- Converts each page to PNG
- Uploads individual pages to `pages/{job_id}/{old|new}/page_XXX.png`

### 2. Orchestrator (Streaming Mode)
**File:** `backend/services/orchestrator.py`

New methods for per-page chaining:
- `create_streaming_job()` - Creates job with per-page stages
- `on_page_ocr_complete()` - Immediately triggers diff for that page
- `on_page_diff_complete()` - Immediately triggers summary for that page
- `on_page_summary_complete()` - Checks if all pages done

### 3. Workers (Streaming Mode)
**Files:**
- `backend/workers/ocr_worker.py` - `process_streaming_message()`
- `backend/workers/diff_worker.py` - `process_streaming_message()`

Workers process single pages and chain to next stage immediately.

### 4. Progress API
**Endpoint:** `GET /api/v1/jobs/{job_id}/progress`

Returns granular per-page, per-stage progress:

```json
{
  "job_id": "abc123",
  "status": "in_progress",
  "total_pages": 3,
  "progress": {
    "ocr": { "completed": 3, "total": 3 },
    "diff": { "completed": 2, "total": 3 },
    "summary": { "completed": 1, "total": 3 }
  },
  "pages": [
    {
      "page_number": 1,
      "drawing_name": "A-101",
      "ocr_status": "completed",
      "diff_status": "completed",
      "summary_status": "completed",
      "diff_result": {
        "diff_result_id": "diff-001",
        "overlay_url": "/api/v1/overlays/diff-001/image",
        "changes_detected": true,
        "change_count": 5
      },
      "summary": {
        "summary_id": "sum-001",
        "summary_text": "Critical: HVAC duct relocated..."
      }
    },
    {
      "page_number": 2,
      "ocr_status": "completed",
      "diff_status": "completed",
      "summary_status": "in_progress"
    },
    {
      "page_number": 3,
      "ocr_status": "completed",
      "diff_status": "in_progress",
      "summary_status": "pending"
    }
  ]
}
```

## Database Schema Changes

### Job Table
```sql
ALTER TABLE jobs ADD COLUMN total_pages INTEGER DEFAULT 1;
```

### JobStage Table
```sql
ALTER TABLE job_stages ADD COLUMN page_number INTEGER;
CREATE INDEX idx_job_stages_page ON job_stages(job_id, page_number);
```

### DiffResult Table
```sql
ALTER TABLE diff_results ADD COLUMN page_number INTEGER DEFAULT 1;
ALTER TABLE diff_results ADD COLUMN drawing_name VARCHAR(255);
CREATE INDEX idx_diff_results_job_page ON diff_results(job_id, page_number);
```

Run migration:
```bash
cd backend
python migrations/add_streaming_columns.py
```

## Fault Tolerance

### Dead Letter Queues
Messages that fail 5 times are sent to DLQ for investigation:
- `buildtrace-dev-ocr-dlq`
- `buildtrace-dev-diff-dlq`
- `buildtrace-dev-summary-dlq`

Setup:
```bash
./scripts/setup_dlq.sh
```

### Per-Page Checkpointing
Each page's `DiffResult` and stage status is committed to database immediately after processing. If a worker crashes, it can resume from the last checkpoint.

### Idempotency
Workers check for existing results before processing:
```python
existing = db.query(DiffResult).filter_by(
    job_id=job_id,
    page_number=page_number
).first()
if existing:
    return existing  # Skip duplicate processing
```

## Frontend Integration

### TypeScript Types
```typescript
// frontend/src/types/index.ts

interface PageProgress {
  page_number: number
  drawing_name?: string
  ocr_status: 'pending' | 'in_progress' | 'completed' | 'failed'
  diff_status: 'pending' | 'in_progress' | 'completed' | 'failed'
  summary_status: 'pending' | 'in_progress' | 'completed' | 'failed'
  diff_result?: { ... }
  summary?: { ... }
}

interface JobProgress {
  job_id: string
  status: string
  total_pages: number
  progress: { ocr, diff, summary }
  pages: PageProgress[]
}
```

### API Client
```typescript
// Poll for streaming progress
const poll = async () => {
  const progress = await apiClient.getJobProgress(jobId)
  setPages(progress.pages)
  
  if (progress.status !== 'completed') {
    setTimeout(poll, 2000)
  }
}
```

### UI Display
```tsx
{pages.map(page => (
  <PageResultCard 
    key={page.page_number}
    pageNumber={page.page_number}
    ocrStatus={page.ocr_status}
    diffStatus={page.diff_status}
    summaryStatus={page.summary_status}
    overlay={page.diff_result?.overlay_url}
    summary={page.summary?.summary_text}
  />
))}
```

## Performance Comparison

| Metric | Batch Mode | Streaming Mode |
|--------|------------|----------------|
| Time to first OCR result | ~60s | **~20s** |
| Time to first overlay | ~150s | **~40s** |
| Time to first summary | ~195s | **~60s** |
| Time to all results | ~195s | ~100s |
| User can start reviewing | After 195s | **After 40s** |

## Configuration

### Environment Variables
```bash
# Enable streaming mode (default: true for new jobs)
STREAMING_PIPELINE_ENABLED=true

# Page extraction DPI
PAGE_EXTRACTION_DPI=220

# Max concurrent messages per worker
PUBSUB_MAX_MESSAGES=1  # For diff worker (memory intensive)
```

## Monitoring

### DLQ Monitoring
```bash
# Check for dead letters
gcloud pubsub subscriptions pull buildtrace-dev-ocr-dlq-sub --limit=10
gcloud pubsub subscriptions pull buildtrace-dev-diff-dlq-sub --limit=10
gcloud pubsub subscriptions pull buildtrace-dev-summary-dlq-sub --limit=10
```

### Logs
```bash
# Worker logs
gcloud logging read "resource.labels.container_name=ocr-worker" --limit=50
gcloud logging read "resource.labels.container_name=diff-worker" --limit=50
gcloud logging read "resource.labels.container_name=summary-worker" --limit=50
```

## Backward Compatibility

The streaming pipeline is additive. Existing batch mode (`create_comparison_job()`) still works:
- Legacy jobs use the old stage tracking
- New streaming jobs use per-page stages
- Both work with the same results API

