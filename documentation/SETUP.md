# BuildTrace Setup Guide

Complete setup instructions for local development and production deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Setup](#production-setup)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Storage Setup](#storage-setup)
7. [Verification](#verification)

## Prerequisites

### Required Software

- **Python 3.11+**: Core runtime
- **PostgreSQL 14+**: Database (for production or local testing)
- **Docker** (optional): For containerized deployment
- **Google Cloud SDK** (for production): `gcloud` CLI tool

### System Dependencies

**macOS:**
```bash
brew install tesseract poppler postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libtesseract-dev \
    postgresql \
    postgresql-contrib \
    libpq-dev
```

**Windows:**
- Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
- Install Poppler from: https://github.com/oschwartz10612/poppler-windows/releases
- Install PostgreSQL from: https://www.postgresql.org/download/windows/

### Python Dependencies

All Python dependencies are listed in `requirements.txt`:
```bash
opencv-python
numpy
matplotlib
scipy
pdf2image
pytesseract
Pillow
openai
python-dotenv
flask
requests
werkzeug
gunicorn
PyMuPDF==1.26.4
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
google-cloud-storage==2.10.0
google-cloud-tasks==2.14.0
alembic==1.12.1
psutil
```

## Local Development Setup

### Step 1: Clone and Navigate

```bash
cd buildtrace-overlay
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env  # If example exists
# Or create manually:
```

```bash
# .env file
ENVIRONMENT=development
DEBUG=true

# Database (optional for local dev)
USE_DATABASE=false
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=postgres
DB_NAME=buildtrace_db

# Storage (local mode)
USE_GCS=false
LOCAL_UPLOAD_PATH=uploads
LOCAL_RESULTS_PATH=results
LOCAL_TEMP_PATH=temp

# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o
USE_AI_ANALYSIS=true

# Application
APP_NAME=BuildTrace
SECRET_KEY=dev-secret-key-change-in-production
HOST=0.0.0.0
PORT=5001

# Processing
DEFAULT_DPI=300
MAX_CONTENT_LENGTH=73400320  # 70MB
PROCESSING_TIMEOUT=3600
```

### Step 5: Create Directories

```bash
mkdir -p uploads results temp data
```

### Step 6: Run the Application

```bash
python app.py
```

The application will be available at: `http://localhost:5001`

### Step 7: Verify Installation

```bash
# Test health endpoint
curl http://localhost:5001/health

# Expected response:
# {"status": "healthy", "environment": "development"}
```

## Production Setup

### Option 1: Google Cloud Run (Recommended)

#### Prerequisites

1. **Google Cloud Project**: Create or select a project
2. **Enable APIs**:
```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    storage-component.googleapis.com \
    artifactregistry.googleapis.com
```

3. **Authenticate**:
```bash
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### Database Setup

See [DATABASE.md](./DATABASE.md) for detailed database setup.

Quick setup:
```bash
# Create Cloud SQL instance
gcloud sql instances create buildtrace-postgres \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database
gcloud sql databases create buildtrace_db \
    --instance=buildtrace-postgres

# Create user
gcloud sql users create buildtrace_user \
    --instance=buildtrace-postgres \
    --password=YOUR_SECURE_PASSWORD
```

#### Storage Setup

```bash
# Create storage bucket
gsutil mb -p buildtrace -c STANDARD -l us-central1 gs://buildtrace-storage

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://buildtrace-storage
```

#### Deploy Application

**Using Cloud Build (Recommended):**
```bash
gcloud builds submit --config=gcp/deployment/cloudbuild.yaml .
```

**Manual Deployment:**
```bash
# Build and push image
docker build -f gcp/deployment/Dockerfile -t \
    us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest .

docker push us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest

# Deploy to Cloud Run
gcloud run deploy buildtrace-overlay \
    --image us-central1-docker.pkg.dev/buildtrace/buildtrace-repo/buildtrace-overlay:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --add-cloudsql-instances buildtrace:us-central1:buildtrace-postgres \
    --set-env-vars ENVIRONMENT=production,INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres
```

### Option 2: Docker Compose (Local Production-like)

```bash
cd gcp/deployment
docker-compose up -d
```

See `gcp/deployment/docker-compose.yml` for configuration.

### Option 3: Traditional Server Deployment

1. **Install dependencies** (see Local Development Setup)
2. **Configure production environment** (see Environment Configuration)
3. **Set up reverse proxy** (nginx, Apache)
4. **Use process manager** (systemd, supervisor)
5. **Configure SSL/TLS** (Let's Encrypt)

Example systemd service:
```ini
[Unit]
Description=BuildTrace Web Application
After=network.target

[Service]
Type=simple
User=buildtrace
WorkingDirectory=/opt/buildtrace
Environment="PATH=/opt/buildtrace/venv/bin"
ExecStart=/opt/buildtrace/venv/bin/gunicorn --bind 0.0.0.0:8080 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Environment Configuration

### Environment Variables Reference

#### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment name (development/production) | `development` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `APP_NAME` | Application name | `BuildTrace` | No |
| `SECRET_KEY` | Flask secret key | `dev-secret-key...` | Yes (prod) |
| `HOST` | Bind host | `0.0.0.0` | No |
| `PORT` | Bind port | `5001` (dev) / `8080` (prod) | No |

#### Database Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `USE_DATABASE` | Enable database mode | `false` (dev) / `true` (prod) | No |
| `DB_HOST` | Database host | `localhost` | If USE_DATABASE=true |
| `DB_PORT` | Database port | `5432` | No |
| `DB_USER` | Database user | `buildtrace_user` | If USE_DATABASE=true |
| `DB_PASS` | Database password | - | If USE_DATABASE=true |
| `DB_NAME` | Database name | `buildtrace_db` | If USE_DATABASE=true |
| `INSTANCE_CONNECTION_NAME` | Cloud SQL instance | - | If Cloud SQL |

#### Storage Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `USE_GCS` | Use Google Cloud Storage | `false` (dev) / `true` (prod) | No |
| `GCS_BUCKET_NAME` | GCS bucket name | `buildtrace-storage` | If USE_GCS=true |
| `LOCAL_UPLOAD_PATH` | Local upload directory | `uploads` | If USE_GCS=false |
| `LOCAL_RESULTS_PATH` | Local results directory | `results` | If USE_GCS=false |
| `LOCAL_TEMP_PATH` | Local temp directory | `temp` | If USE_GCS=false |

#### OpenAI Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes |
| `OPENAI_MODEL` | Model to use | `gpt-4o` | No |
| `USE_AI_ANALYSIS` | Enable AI analysis | `true` | No |

#### Processing Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEFAULT_DPI` | Default DPI for PDF conversion | `300` | No |
| `MAX_CONTENT_LENGTH` | Max upload size (bytes) | `73400320` (70MB) | No |
| `PROCESSING_TIMEOUT` | Processing timeout (seconds) | `3600` | No |
| `MAX_SYNC_PAGES` | Max pages for sync processing | `10` | No |
| `MEMORY_LIMIT_GB` | Memory limit for processing | `10.0` (dev) / `25.0` (prod) | No |

### Configuration File Loading Order

1. Environment variables (highest priority)
2. `.env.{ENVIRONMENT}` file (e.g., `.env.production`)
3. `.env` file
4. Default values (lowest priority)

## Database Setup

### Local PostgreSQL

```bash
# Create database
createdb buildtrace_db

# Or using psql
psql -U postgres
CREATE DATABASE buildtrace_db;
CREATE USER buildtrace_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE buildtrace_db TO buildtrace_user;
\q
```

### Initialize Schema

```bash
# Using Python
python -c "from gcp.database import init_db; init_db()"

# Or using Flask CLI (if configured)
flask db init
flask db migrate
flask db upgrade
```

### Cloud SQL Setup

See `gcp/docs/DATABASE_SETUP_GUIDE.md` for detailed Cloud SQL setup.

Quick reference:
```bash
# Create instance
gcloud sql instances create buildtrace-postgres \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database
gcloud sql databases create buildtrace_db \
    --instance=buildtrace-postgres

# Create user
gcloud sql users create buildtrace_user \
    --instance=buildtrace-postgres \
    --password=YOUR_PASSWORD
```

### Cloud SQL Proxy (Local Development)

```bash
# Download proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 \
    -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Run proxy
./cloud_sql_proxy -instances=buildtrace:us-central1:buildtrace-postgres=tcp:5432

# In another terminal, set environment
export USE_CLOUD_SQL_AUTH_PROXY=true
export DB_HOST=127.0.0.1
export DB_PORT=5432
```

## Storage Setup

### Local Storage

No setup required. Directories are created automatically:
- `uploads/`: Uploaded files
- `results/`: Processing results
- `temp/`: Temporary files

### Google Cloud Storage

```bash
# Create bucket
gsutil mb -p buildtrace -c STANDARD -l us-central1 gs://buildtrace-storage

# Set CORS (if needed for direct browser uploads)
gsutil cors set cors.json gs://buildtrace-storage

# Set lifecycle policy (optional)
gsutil lifecycle set lifecycle.json gs://buildtrace-storage
```

**Bucket Structure:**
```
buildtrace-storage/
├── sessions/
│   └── {session_id}/
│       ├── uploads/
│       └── results/
└── drawings/
```

## Verification

### Health Check

```bash
curl http://localhost:5001/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "database": "connected",
  "storage": "local"
}
```

### Test Database Connection

```bash
python -c "
from gcp.database import get_db_session
with get_db_session() as db:
    print('Database connection: OK')
"
```

### Test Storage

```bash
python -c "
from gcp.storage import storage_service
print('Storage type:', storage_service.get_storage_config()['type'])
print('Storage: OK')
"
```

### Test OpenAI Connection

```bash
python -c "
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('OpenAI connection: OK')
"
```

### Test File Upload

```bash
# Using curl
curl -X POST http://localhost:5001/upload \
  -F "old_file=@test_old.pdf" \
  -F "new_file=@test_new.pdf"
```

### Test Processing Pipeline

```bash
python -c "
from complete_drawing_pipeline import complete_drawing_pipeline
results = complete_drawing_pipeline(
    'test_old.pdf',
    'test_new.pdf',
    dpi=300,
    debug=True
)
print('Pipeline test: OK')
print(f'Overlays created: {results[\"summary\"][\"overlays_created\"]}')
"
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Database Connection Failed**
   ```bash
   # Check PostgreSQL is running
   pg_isready
   
   # Check connection string
   echo $DATABASE_URL
   ```

3. **Tesseract Not Found**
   ```bash
   # macOS
   brew install tesseract
   
   # Linux
   sudo apt-get install tesseract-ocr
   ```

4. **OpenCV Import Error**
   ```bash
   # Reinstall opencv
   pip uninstall opencv-python
   pip install opencv-python
   ```

5. **Port Already in Use**
   ```bash
   # Change port in .env
   PORT=5002
   ```

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for more detailed troubleshooting.

## Next Steps

- [API.md](./API.md): Learn about API endpoints
- [DEVELOPMENT.md](./DEVELOPMENT.md): Development workflow
- [DEPLOYMENT.md](./DEPLOYMENT.md): Production deployment guide

