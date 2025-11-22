# BuildTrace Backend

Flask-based API backend for BuildTrace with async job processing via Pub/Sub.

## Architecture

- **Flask API**: Lightweight REST API for handling requests
- **Pub/Sub**: Google Cloud Pub/Sub for async job queue
- **Workers**: Separate worker services for OCR, Diff, and Summary processing
- **Database**: PostgreSQL with Cloud SQL support
- **Storage**: Google Cloud Storage with local fallback

## Directory Structure

```
backend/
├── app.py                    # Main Flask application
├── config.py                 # Configuration management
├── blueprints/               # Flask blueprints (to be implemented)
│   ├── auth.py
│   ├── projects.py
│   ├── drawings.py
│   ├── jobs.py
│   ├── overlays.py
│   └── summaries.py
├── services/                 # Business logic services
│   ├── orchestrator.py       # Job orchestration
│   ├── job_service.py        # Job state management
│   └── storage_service.py    # Unified storage interface
├── workers/                  # Worker services (to be implemented)
│   ├── ocr_worker.py
│   ├── diff_worker.py
│   └── summary_worker.py
├── processing/               # Processing pipelines (to be extracted)
│   ├── ocr_pipeline.py
│   ├── diff_pipeline.py
│   └── summary_pipeline.py
├── gcp/
│   ├── database/             # Database models and connection
│   ├── pubsub/               # Pub/Sub publisher/subscriber
│   └── storage/              # Storage service
└── utils/                    # Utility functions
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
ENVIRONMENT=development
USE_DATABASE=true
USE_GCS=false
USE_PUBSUB=false
GCP_PROJECT_ID=buildtrace-dev
DB_HOST=localhost
DB_PORT=5432
DB_NAME=buildtrace_db
DB_USER=postgres
DB_PASS=postgres
```

### 3. Set Up Database

Run the migration script:

```bash
psql -U postgres -d buildtrace_db -f migrations/001_create_new_tables.sql
```

Or use SQLAlchemy to create tables:

```python
from gcp.database import init_db
init_db()
```

### 4. Set Up Pub/Sub (Production)

```bash
./scripts/setup_pubsub.sh
```

### 5. Run via Docker Compose (optional)

From the repository root:

```bash
docker compose up --build
```

This starts Postgres, the Flask API (on port 5001), and the Next.js frontend (on port 3000) using the configuration from `docker-compose.yml`. The backend runs with synchronous worker fallback for local testing; set `USE_PUBSUB=true` and wire Pub/Sub credentials for a cloud deployment.

## Running

### Development

```bash
python app.py
```

### Production

```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

## API Endpoints

### Health Check

```
GET /health
```

Returns system status and configuration.

## Development Status

### Phase 1: Foundation (Current)
- ✅ Directory structure created
- ✅ Configuration management
- ✅ Database models (new schema)
- ✅ Pub/Sub client library
- ✅ Storage service
- ✅ Migration scripts
- ⏳ Pub/Sub topics setup (script ready)

### Phase 2: Orchestrator & Job Management (Next)
- ⏳ Orchestrator service
- ⏳ Job management API endpoints
- ⏳ Drawing upload endpoint

### Phase 3: Processing Pipeline Extraction
- ⏳ Extract OCR logic
- ⏳ Extract diff logic
- ⏳ Extract summary logic

### Phase 4: Worker Implementation
- ⏳ OCR worker
- ⏳ Diff worker
- ⏳ Summary worker

## Notes

- The new architecture uses `jobs` and `job_stages` tables instead of `processing_jobs`
- Legacy tables (`comparisons`, `analysis_results`) are kept for backward compatibility
- Frontend and backend development should happen simultaneously for faster iteration
