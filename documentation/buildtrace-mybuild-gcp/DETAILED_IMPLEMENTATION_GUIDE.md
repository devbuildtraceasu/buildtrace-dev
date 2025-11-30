# BuildTrace System - Detailed Implementation Guide

## Table of Contents
1. [Phase 1: GCP Console Setup & Infrastructure](#phase-1-gcp-console-setup--infrastructure)
2. [Phase 2: Application Development](#phase-2-application-development)
3. [Phase 3: Containerization & Deployment](#phase-3-containerization--deployment)
4. [Phase 4: Testing & Validation](#phase-4-testing--validation)
5. [Phase 5: Documentation & Delivery](#phase-5-documentation--delivery)
6. [Phase 6: Stretch Goals](#phase-6-stretch-goals)
7. [Phase 7: Monitoring & Observability](#phase-7-monitoring--observability)

---

## Phase 1: GCP Console Setup & Infrastructure

### 1.1 GCP Project Setup

#### Task: Create or Select GCP Project

**Steps:**
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "NEW PROJECT" or select existing project
4. Enter project name: `buildtrace-system` (or your preferred name)
5. Note the Project ID (e.g., `buildtrace-system-123456`)
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
   - Editor + Security Admin roles (minimum)

**Store Project Information:**
```bash
# Set these as environment variables
export PROJECT_ID="buildtrace-system-123456"
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export REGION="us-west2"  # Choose your preferred region
```

---

### 1.2 Enable Required GCP APIs

#### Task: Enable All Required APIs

**Via GCP Console:**
1. Navigate to "APIs & Services" > "Library"
2. Search and enable each API:
   - **Cloud Run Admin API** (`run.googleapis.com`) - Note: This is the official name, sometimes shortened to "Cloud Run API"
   - Cloud Pub/Sub API (`pubsub.googleapis.com`)
   - Cloud Tasks API (`cloudtasks.googleapis.com`)
   - Cloud Storage API (`storage-component.googleapis.com`)
   - Cloud SQL Admin API (`sqladmin.googleapis.com`) OR BigQuery API (`bigquery.googleapis.com`)
   - Cloud Build API (`cloudbuild.googleapis.com`)
   - Artifact Registry API (`artifactregistry.googleapis.com`)

**Via gcloud CLI (Faster):**
```bash
# Set project
gcloud config set project $PROJECT_ID

# Enable all APIs at once
gcloud services enable \
  run.googleapis.com \
  pubsub.googleapis.com \
  cloudtasks.googleapis.com \
  storage-component.googleapis.com \
  sqladmin.googleapis.com \
  bigquery.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

**Expected Output:**
- All APIs should show status "ENABLED"
- This may take 1-2 minutes

---

### 1.3 Cloud Storage Setup

#### Task: Create Storage Buckets

**Step 1: Create Input Bucket**
```bash
# Create bucket for input JSON files
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-input-$PROJECT_ID

# Or via console:
# 1. Navigate to "Cloud Storage" > "Buckets"
# 2. Click "CREATE BUCKET"
# 3. Name: buildtrace-input-{project-id}
# 4. Location type: Region
# 5. Region: us-west2 (or your chosen region)
# 6. Storage class: Standard
# 7. Access control: Uniform
```

**Step 2: Create Output Bucket**
```bash
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://buildtrace-output-$PROJECT_ID
```

**Step 3: Create Folder Structure**
```bash
# Create folders in input bucket
gsutil mkdir gs://buildtrace-input-$PROJECT_ID/input/
gsutil mkdir gs://buildtrace-input-$PROJECT_ID/processed/
gsutil mkdir gs://buildtrace-input-$PROJECT_ID/failed/

# Create folders in output bucket
gsutil mkdir gs://buildtrace-output-$PROJECT_ID/results/
gsutil mkdir gs://buildtrace-output-$PROJECT_ID/metrics/
```

**Step 4: Set Bucket Permissions**
```bash
# Make buckets private (only service account can access)
gsutil iam ch allUsers:objectViewer gs://buildtrace-input-$PROJECT_ID  # Remove public access
gsutil iam ch allUsers:objectViewer gs://buildtrace-output-$PROJECT_ID  # Remove public access

# Grant service account access (we'll do this after creating service account)
# gsutil iam ch serviceAccount:buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://buildtrace-input-$PROJECT_ID
```

**Step 5: Configure Lifecycle (Optional)**
```bash
# Create lifecycle policy file (lifecycle.json)
cat > lifecycle.json << EOF
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
EOF

# Apply lifecycle policy
gsutil lifecycle set lifecycle.json gs://buildtrace-input-$PROJECT_ID
```

---

### 1.4 Database Setup

#### Option A: Cloud SQL (PostgreSQL)

**Step 1: Create Cloud SQL Instance**

**Via Console:**
1. Navigate to "SQL" > "Create Instance"
2. Choose "PostgreSQL"
3. Instance ID: `buildtrace-db`
4. Root password: Set a strong password (save it securely!)
5. Region: Same as your project region
6. Database version: PostgreSQL 15 (or latest)
7. Machine type: db-f1-micro (for testing) or db-n1-standard-1 (for production)
8. Storage: 10 GB SSD
9. Click "CREATE"

**Via gcloud CLI:**
```bash
# Create Cloud SQL instance
gcloud sql instances create buildtrace-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password=YOUR_SECURE_PASSWORD \
  --storage-type=SSD \
  --storage-size=10GB

# Note: Replace YOUR_SECURE_PASSWORD with a strong password
```

**Step 2: Create Database**
```bash
# Create database
gcloud sql databases create buildtrace_db --instance=buildtrace-db

# Create database user
gcloud sql users create buildtrace_user \
  --instance=buildtrace-db \
  --password=YOUR_DB_USER_PASSWORD
```

**Step 3: Get Connection Details**
```bash
# Get connection name
gcloud sql instances describe buildtrace-db --format="value(connectionName)"
# Output: project-id:region:buildtrace-db

# Get public IP (if using public IP)
gcloud sql instances describe buildtrace-db --format="value(ipAddresses[0].ipAddress)"
```

**Step 4: Create Database Schema**

Create SQL file (`schema.sql`):
```sql
-- Table: drawing_pairs
CREATE TABLE IF NOT EXISTS drawing_pairs (
    id SERIAL PRIMARY KEY,
    drawing_id VARCHAR(255) NOT NULL,
    version_a_path VARCHAR(500) NOT NULL,
    version_b_path VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(drawing_id, version_a_path, version_b_path)
);

-- Table: change_results
CREATE TABLE IF NOT EXISTS change_results (
    id SERIAL PRIMARY KEY,
    drawing_id VARCHAR(255) NOT NULL,
    job_id VARCHAR(255),
    added JSONB,
    removed JSONB,
    moved JSONB,
    summary TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drawing_id) REFERENCES drawing_pairs(drawing_id)
);

-- Table: processing_metrics
CREATE TABLE IF NOT EXISTS processing_metrics (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    drawing_id VARCHAR(255),
    latency_ms INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    added_count INTEGER DEFAULT 0,
    removed_count INTEGER DEFAULT 0,
    moved_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: anomalies
CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    drawing_id VARCHAR(255),
    anomaly_type VARCHAR(100) NOT NULL,
    details JSONB,
    severity VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_drawing_pairs_drawing_id ON drawing_pairs(drawing_id);
CREATE INDEX idx_change_results_drawing_id ON change_results(drawing_id);
CREATE INDEX idx_processing_metrics_created_at ON processing_metrics(created_at);
CREATE INDEX idx_processing_metrics_status ON processing_metrics(status);
CREATE INDEX idx_anomalies_created_at ON anomalies(created_at);
```

**Apply Schema:**
```bash
# Connect to database and run schema
gcloud sql connect buildtrace-db --user=buildtrace_user --database=buildtrace_db

# Or using psql directly
psql "host=/cloudsql/$PROJECT_ID:$REGION:buildtrace-db dbname=buildtrace_db user=buildtrace_user" < schema.sql
```

#### Option B: BigQuery

**Step 1: Create BigQuery Dataset**
```bash
# Create dataset
bq mk --dataset --location=$REGION buildtrace

# Or via console:
# 1. Navigate to "BigQuery" > "Datasets"
# 2. Click "CREATE DATASET"
# 3. Dataset ID: buildtrace
# 4. Location: us-west2
```

**Step 2: Create Tables**

```bash
# Create drawing_pairs table
bq mk --table buildtrace.drawing_pairs \
  drawing_id:STRING,version_a_path:STRING,version_b_path:STRING,status:STRING,created_at:TIMESTAMP,updated_at:TIMESTAMP

# Create change_results table
bq mk --table buildtrace.change_results \
  drawing_id:STRING,job_id:STRING,added:JSON,removed:JSON,moved:JSON,summary:STRING,processing_time_ms:INTEGER,created_at:TIMESTAMP

# Create processing_metrics table
bq mk --table buildtrace.processing_metrics \
  job_id:STRING,drawing_id:STRING,latency_ms:INTEGER,status:STRING,added_count:INTEGER,removed_count:INTEGER,moved_count:INTEGER,created_at:TIMESTAMP

# Create anomalies table
bq mk --table buildtrace.anomalies \
  drawing_id:STRING,anomaly_type:STRING,details:JSON,severity:STRING,created_at:TIMESTAMP
```

---

### 1.5 Pub/Sub Setup

#### Task: Create Pub/Sub Topics and Subscriptions

**Step 1: Create Main Topic**
```bash
# Create topic for processing tasks
gcloud pubsub topics create drawing-processing-tasks

# Or via console:
# 1. Navigate to "Pub/Sub" > "Topics"
# 2. Click "CREATE TOPIC"
# 3. Topic ID: drawing-processing-tasks
# 4. Click "CREATE"
```

**Step 2: Create Dead-Letter Topic**
```bash
gcloud pubsub topics create drawing-processing-dlq
```

**Step 3: Create Push Subscription**
```bash
# First, get your Cloud Run service URL (after deploying worker)
# Then create subscription
gcloud pubsub subscriptions create drawing-processing-workers \
  --topic=drawing-processing-tasks \
  --push-endpoint=https://buildtrace-worker-XXXXX-uc.a.run.app/process-drawing \
  --ack-deadline=600 \
  --dead-letter-topic=drawing-processing-dlq \
  --max-delivery-attempts=5

# Note: Replace the push-endpoint with your actual Cloud Run URL
# We'll update this after deploying the worker service
```

**Step 4: Create Dead-Letter Subscription**
```bash
gcloud pubsub subscriptions create drawing-processing-dlq-sub \
  --topic=drawing-processing-dlq
```

**Configure via Console:**
1. Navigate to "Pub/Sub" > "Subscriptions"
2. Click "CREATE SUBSCRIPTION"
3. Subscription ID: `drawing-processing-workers`
4. Topic: `drawing-processing-tasks`
5. Delivery type: Push
6. Endpoint URL: (Your Cloud Run worker URL)
7. Acknowledgment deadline: 600 seconds
8. Enable dead letter queue: Yes
9. Dead letter topic: `drawing-processing-dlq`
10. Max delivery attempts: 5

---

### 1.6 Cloud Tasks Setup (Alternative to Pub/Sub)

#### Task: Create Cloud Tasks Queue

**Via Console:**
1. Navigate to "Cloud Tasks" > "Queues"
2. Click "CREATE QUEUE"
3. Queue name: `drawing-processing-queue`
4. Location: Same as your project region
5. Configure:
   - Max attempts: 5
   - Max retry duration: 3600s
   - Min backoff: 10s
   - Max backoff: 300s
   - Max doubling: 5

**Via gcloud CLI:**
```bash
gcloud tasks queues create drawing-processing-queue \
  --location=$REGION \
  --max-attempts=5 \
  --max-retry-duration=3600s \
  --min-backoff=10s \
  --max-backoff=300s \
  --max-doublings=5
```

---

### 1.7 Service Account Setup

#### Task: Create and Configure Service Account

**Step 1: Create Service Account**
```bash
# Create service account
gcloud iam service-accounts create buildtrace-service-account \
  --display-name="BuildTrace Service Account" \
  --description="Service account for BuildTrace system"

# Or via console:
# 1. Navigate to "IAM & Admin" > "Service Accounts"
# 2. Click "CREATE SERVICE ACCOUNT"
# 3. Name: buildtrace-service-account
# 4. Description: Service account for BuildTrace system
```

**Step 2: Grant Required Roles**
```bash
# Get service account email
export SERVICE_ACCOUNT_EMAIL="buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com"

# Grant roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/pubsub.publisher"

# For Cloud SQL
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"

# OR for BigQuery
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/bigquery.dataEditor"

# Logging
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/logging.logWriter"
```

**Step 3: Generate Service Account Key (for local testing)**
```bash
# Create key file
gcloud iam service-accounts keys create buildtrace-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

# Set environment variable for local use
export GOOGLE_APPLICATION_CREDENTIALS="./buildtrace-key.json"

# Add to .gitignore (IMPORTANT!)
echo "buildtrace-key.json" >> .gitignore
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
  --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

---

## Phase 2: Application Development

### 2.1 Project Structure Setup

#### Task: Create Project Directory Structure

**Create Directory Structure:**
```bash
mkdir -p buildtrace/{api,workers,simulators,infra,tests}
cd buildtrace

# Create initial files
touch Dockerfile.api Dockerfile.worker
touch requirements.txt  # For Python
touch .gitignore
touch README.md
```

**Directory Structure:**
```
buildtrace/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── process.py       # POST /process endpoint
│   │   ├── changes.py       # GET /changes endpoint
│   │   ├── metrics.py       # GET /metrics endpoint
│   │   └── health.py        # GET /health endpoint
│   ├── models/
│   │   ├── __init__.py
│   │   ├── drawing.py       # Drawing data models
│   │   └── changes.py       # Change result models
│   └── utils/
│       ├── __init__.py
│       ├── database.py      # Database connection
│       └── pubsub.py        # Pub/Sub client
├── workers/
│   ├── __init__.py
│   ├── main.py              # Worker entry point
│   ├── processor.py         # Drawing comparison logic
│   └── metrics.py           # Metrics collection
├── simulators/
│   ├── __init__.py
│   └── data_generator.py    # Generate test data
├── infra/
│   ├── terraform/           # Optional: Terraform configs
│   └── scripts/
│       └── deploy.sh        # Deployment script
├── tests/
│   ├── __init__.py
│   ├── test_processor.py
│   └── test_api.py
├── Dockerfile.api
├── Dockerfile.worker
├── requirements.txt
├── .gitignore
└── README.md
```

**Create .gitignore:**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
dist/
*.egg-info/

# Environment
.env
*.json  # Service account keys
buildtrace-key.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

### 2.2 Core Change Detection Logic

#### Task: Implement Drawing Comparison Algorithm

**Create `api/models/drawing.py`:**
```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DrawingObject(BaseModel):
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float

class DrawingVersion(BaseModel):
    objects: List[DrawingObject]

class ChangeResult(BaseModel):
    added: List[str]
    removed: List[str]
    moved: List[str]
    summary: str
```

**Create `workers/processor.py`:**
```python
from typing import List, Dict, Tuple
from api.models.drawing import DrawingObject, DrawingVersion, ChangeResult

def parse_drawing_json(json_data: List[Dict]) -> DrawingVersion:
    """Parse JSON data into DrawingVersion object."""
    objects = []
    for obj in json_data:
        try:
            drawing_obj = DrawingObject(
                id=obj["id"],
                type=obj["type"],
                x=float(obj["x"]),
                y=float(obj["y"]),
                width=float(obj["width"]),
                height=float(obj["height"])
            )
            objects.append(drawing_obj)
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid drawing object: {obj}, Error: {e}")
    
    return DrawingVersion(objects=objects)

def detect_changes(version_a: DrawingVersion, version_b: DrawingVersion) -> ChangeResult:
    """
    Compare two drawing versions and detect changes.
    
    Args:
        version_a: Previous version
        version_b: Current version
    
    Returns:
        ChangeResult with detected changes
    """
    # Create dictionaries for quick lookup
    objects_a = {obj.id: obj for obj in version_a.objects}
    objects_b = {obj.id: obj for obj in version_b.objects}
    
    added = []
    removed = []
    moved = []
    
    # Find added objects (in B but not in A)
    for obj_id, obj in objects_b.items():
        if obj_id not in objects_a:
            added.append(f"{obj_id} ({obj.type} at {obj.x},{obj.y})")
    
    # Find removed objects (in A but not in B)
    for obj_id, obj in objects_a.items():
        if obj_id not in objects_b:
            removed.append(f"{obj_id} ({obj.type})")
    
    # Find moved objects (same ID but different position)
    for obj_id in objects_a:
        if obj_id in objects_b:
            obj_a = objects_a[obj_id]
            obj_b = objects_b[obj_id]
            
            # Check if position changed (using a threshold for floating point comparison)
            threshold = 0.1
            if (abs(obj_a.x - obj_b.x) > threshold or 
                abs(obj_a.y - obj_b.y) > threshold):
                dx = obj_b.x - obj_a.x
                dy = obj_b.y - obj_a.y
                
                # Determine direction
                if abs(dx) > abs(dy):
                    direction = "east" if dx > 0 else "west"
                    distance = abs(dx)
                else:
                    direction = "north" if dy > 0 else "south"
                    distance = abs(dy)
                
                moved.append(f"{obj_id} moved {distance:.1f} units {direction}")
    
    # Generate natural language summary
    summary = generate_summary(added, removed, moved)
    
    return ChangeResult(
        added=added,
        removed=removed,
        moved=moved,
        summary=summary
    )

def generate_summary(added: List[str], removed: List[str], moved: List[str]) -> str:
    """Generate natural language summary of changes."""
    parts = []
    
    if moved:
        parts.append(f"{len(moved)} object(s) moved: {', '.join(moved[:3])}")
        if len(moved) > 3:
            parts.append(f"and {len(moved) - 3} more")
    
    if added:
        parts.append(f"{len(added)} object(s) added: {', '.join(added[:3])}")
        if len(added) > 3:
            parts.append(f"and {len(added) - 3} more")
    
    if removed:
        parts.append(f"{len(removed)} object(s) removed: {', '.join(removed[:3])}")
        if len(removed) > 3:
            parts.append(f"and {len(removed) - 3} more")
    
    if not parts:
        return "No changes detected."
    
    return ". ".join(parts) + "."
```

**Add Input Validation:**
```python
import json
from typing import Dict, Any

def validate_json_format(data: Any) -> bool:
    """Validate JSON follows expected format."""
    if not isinstance(data, list):
        return False
    
    required_fields = {"id", "type", "x", "y", "width", "height"}
    
    for obj in data:
        if not isinstance(obj, dict):
            return False
        if not required_fields.issubset(obj.keys()):
            return False
        # Validate types
        try:
            float(obj["x"])
            float(obj["y"])
            float(obj["width"])
            float(obj["height"])
        except (ValueError, TypeError):
            return False
    
    return True
```

---

### 2.3 API Endpoints (FastAPI)

#### Task: Implement API Endpoints

**Create `api/main.py`:**
```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from api.utils.database import get_db_connection
from api.utils.pubsub import publish_task

app = FastAPI(title="BuildTrace API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "drawing-processing-tasks")
INPUT_BUCKET = os.getenv("INPUT_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")

@app.get("/")
async def root():
    return {"message": "BuildTrace API", "status": "running"}

# Import routers
from api.routers import process, changes, metrics, health

app.include_router(process.router, prefix="/process", tags=["processing"])
app.include_router(changes.router, prefix="/changes", tags=["changes"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(health.router, prefix="/health", tags=["health"])
```

**Create `api/routers/process.py`:**
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json
from google.cloud import storage, pubsub_v1
import os

router = APIRouter()

class ProcessRequest(BaseModel):
    version_pairs: Optional[List[Dict[str, str]]] = None
    storage_path: Optional[str] = None

class ProcessResponse(BaseModel):
    job_id: str
    message: str
    tasks_created: int

@router.post("", response_model=ProcessResponse)
async def process_drawings(request: ProcessRequest):
    """
    Accept drawing version pairs and queue them for processing.
    
    Request body can contain:
    - version_pairs: List of {"drawing_id": "...", "version_a": "...", "version_b": "..."}
    - storage_path: Path to Cloud Storage folder containing JSON files
    """
    project_id = os.getenv("PROJECT_ID")
    topic_name = os.getenv("PUBSUB_TOPIC", "drawing-processing-tasks")
    
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    
    job_id = str(uuid.uuid4())
    tasks_created = 0
    
    if request.version_pairs:
        # Process direct version pairs
        for pair in request.version_pairs:
            message_data = {
                "job_id": job_id,
                "drawing_id": pair.get("drawing_id"),
                "version_a": pair.get("version_a"),
                "version_b": pair.get("version_b")
            }
            
            message_bytes = json.dumps(message_data).encode("utf-8")
            publisher.publish(topic_path, message_bytes)
            tasks_created += 1
    
    elif request.storage_path:
        # Process from Cloud Storage
        storage_client = storage.Client()
        bucket_name, prefix = request.storage_path.replace("gs://", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        
        # List all JSON files in the path
        blobs = bucket.list_blobs(prefix=prefix)
        json_files = [blob for blob in blobs if blob.name.endswith(".json")]
        
        # Group files by drawing_id (assuming naming convention)
        # This is a simplified version - adjust based on your file naming
        for blob in json_files:
            # Extract drawing_id from filename (adjust logic as needed)
            drawing_id = blob.name.split("/")[-1].replace(".json", "")
            
            message_data = {
                "job_id": job_id,
                "drawing_id": drawing_id,
                "storage_path": blob.name
            }
            
            message_bytes = json.dumps(message_data).encode("utf-8")
            publisher.publish(topic_path, message_bytes)
            tasks_created += 1
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either version_pairs or storage_path must be provided"
        )
    
    return ProcessResponse(
        job_id=job_id,
        message=f"Queued {tasks_created} tasks for processing",
        tasks_created=tasks_created
    )
```

**Create `api/routers/changes.py`:**
```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.models.changes import ChangeResult
from api.utils.database import get_db_connection
import os

router = APIRouter()

@router.get("", response_model=ChangeResult)
async def get_changes(drawing_id: str = Query(..., description="Drawing ID to retrieve changes for")):
    """
    Retrieve detected changes for a specific drawing.
    """
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        # Query change results
        cursor.execute("""
            SELECT added, removed, moved, summary
            FROM change_results
            WHERE drawing_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (drawing_id,))
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No changes found for drawing_id: {drawing_id}"
            )
        
        return ChangeResult(
            added=result[0] if result[0] else [],
            removed=result[1] if result[1] else [],
            moved=result[2] if result[2] else [],
            summary=result[3] or "No summary available"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        db.close()
```

**Create `api/routers/metrics.py`:**
```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from api.utils.database import get_db_connection
from datetime import datetime, timedelta
import statistics

router = APIRouter()

class MetricsResponse(BaseModel):
    hourly_stats: Dict[str, Dict[str, int]]
    latency_p95: float
    latency_p99: float
    data_quality_issues: int

@router.get("", response_model=MetricsResponse)
async def get_metrics():
    """
    Return processing metrics including latency percentiles and hourly statistics.
    """
    db = get_db_connection()
    cursor = db.cursor()
    
    # Get last 24 hours of metrics
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
    
    # Hourly aggregation
    cursor.execute("""
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            SUM(added_count) as total_added,
            SUM(removed_count) as total_removed,
            SUM(moved_count) as total_moved
        FROM processing_metrics
        WHERE created_at >= %s
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour
    """, (twenty_four_hours_ago,))
    
    hourly_stats = {}
    for row in cursor.fetchall():
        hour_key = row[0].isoformat()
        hourly_stats[hour_key] = {
            "added": row[1] or 0,
            "removed": row[2] or 0,
            "moved": row[3] or 0
        }
    
    # Calculate latency percentiles
    cursor.execute("""
        SELECT latency_ms
        FROM processing_metrics
        WHERE created_at >= %s AND status = 'completed'
        ORDER BY latency_ms
    """, (twenty_four_hours_ago,))
    
    latencies = [row[0] for row in cursor.fetchall()]
    
    if latencies:
        p95_index = int(len(latencies) * 0.95)
        p99_index = int(len(latencies) * 0.99)
        latency_p95 = latencies[p95_index] if p95_index < len(latencies) else latencies[-1]
        latency_p99 = latencies[p99_index] if p99_index < len(latencies) else latencies[-1]
    else:
        latency_p95 = 0.0
        latency_p99 = 0.0
    
    # Data quality issues count
    cursor.execute("""
        SELECT COUNT(*)
        FROM anomalies
        WHERE created_at >= %s
    """, (twenty_four_hours_ago,))
    
    data_quality_issues = cursor.fetchone()[0] or 0
    
    cursor.close()
    db.close()
    
    return MetricsResponse(
        hourly_stats=hourly_stats,
        latency_p95=latency_p95,
        latency_p99=latency_p99,
        data_quality_issues=data_quality_issues
    )
```

**Create `api/routers/health.py`:**
```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
from api.utils.database import get_db_connection
from datetime import datetime, timedelta

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    warnings: List[str]
    anomalies: List[Dict]

@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint with anomaly detection.
    """
    db = get_db_connection()
    cursor = db.cursor()
    warnings = []
    anomalies_list = []
    
    # Check for missing/delayed uploads
    # (This is simplified - adjust based on your expected upload schedule)
    one_hour_ago = datetime.now() - timedelta(hours=1)
    cursor.execute("""
        SELECT COUNT(*)
        FROM drawing_pairs
        WHERE status = 'pending' AND created_at < %s
    """, (one_hour_ago,))
    
    delayed_count = cursor.fetchone()[0] or 0
    if delayed_count > 0:
        warnings.append(f"{delayed_count} drawing pairs delayed for more than 1 hour")
    
    # Detect spike in changes (10x increase)
    cursor.execute("""
        SELECT 
            drawing_id,
            COUNT(*) as change_count,
            MAX(created_at) as last_change
        FROM change_results
        WHERE created_at >= %s
        GROUP BY drawing_id
        HAVING COUNT(*) > 10
        ORDER BY change_count DESC
        LIMIT 10
    """, (datetime.now() - timedelta(hours=24),))
    
    recent_changes = cursor.fetchall()
    
    # Get previous period for comparison
    cursor.execute("""
        SELECT 
            drawing_id,
            COUNT(*) as change_count
        FROM change_results
        WHERE created_at >= %s AND created_at < %s
        GROUP BY drawing_id
    """, (
        datetime.now() - timedelta(hours=48),
        datetime.now() - timedelta(hours=24)
    ))
    
    previous_changes = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Check for spikes
    for drawing_id, current_count, last_change in recent_changes:
        previous_count = previous_changes.get(drawing_id, 0)
        if previous_count > 0 and current_count >= previous_count * 10:
            anomalies_list.append({
                "drawing_id": drawing_id,
                "type": "spike_detected",
                "details": f"Change count increased from {previous_count} to {current_count} ({(current_count/previous_count):.1f}x increase)",
                "timestamp": last_change.isoformat()
            })
            warnings.append(f"Spike detected for drawing {drawing_id}: {current_count} changes (10x increase)")
    
    # Get recent anomalies from anomalies table
    cursor.execute("""
        SELECT drawing_id, anomaly_type, details, created_at
        FROM anomalies
        WHERE created_at >= %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (datetime.now() - timedelta(hours=24),))
    
    for row in cursor.fetchall():
        anomalies_list.append({
            "drawing_id": row[0],
            "type": row[1],
            "details": row[2],
            "timestamp": row[3].isoformat()
        })
    
    cursor.close()
    db.close()
    
    status = "healthy" if not warnings else "degraded"
    
    return HealthResponse(
        status=status,
        warnings=warnings,
        anomalies=anomalies_list
    )
```

---

### 2.4 Worker Implementation

#### Task: Create Worker Service

**Create `workers/main.py`:**
```python
from fastapi import FastAPI, Request, HTTPException
from google.cloud import pubsub_v1, storage
from workers.processor import detect_changes, parse_drawing_json
from api.utils.database import get_db_connection
import json
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BuildTrace Worker")

PROJECT_ID = os.getenv("PROJECT_ID")
INPUT_BUCKET = os.getenv("INPUT_BUCKET")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")

@app.post("/process-drawing")
async def process_drawing(request: Request):
    """
    Pub/Sub push endpoint for processing drawing pairs.
    """
    try:
        # Parse Pub/Sub message
        envelope = await request.json()
        message_data = json.loads(
            base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        )
        
        job_id = message_data.get("job_id")
        drawing_id = message_data.get("drawing_id")
        start_time = time.time()
        
        logger.info(f"Processing job {job_id}, drawing {drawing_id}")
        
        # Get version data
        if "storage_path" in message_data:
            # Load from Cloud Storage
            version_a, version_b = load_from_storage(message_data["storage_path"])
        else:
            # Load from message
            version_a = parse_drawing_json(json.loads(message_data["version_a"]))
            version_b = parse_drawing_json(json.loads(message_data["version_b"]))
        
        # Detect changes
        changes = detect_changes(version_a, version_b)
        
        # Store results in database
        store_results(job_id, drawing_id, changes, start_time)
        
        # Update metrics
        processing_time = int((time.time() - start_time) * 1000)
        store_metrics(job_id, drawing_id, processing_time, changes)
        
        # Check for anomalies
        check_anomalies(drawing_id, changes)
        
        logger.info(f"Completed processing {drawing_id} in {processing_time}ms")
        
        return {"status": "success", "job_id": job_id, "drawing_id": drawing_id}
    
    except Exception as e:
        logger.error(f"Error processing drawing: {str(e)}", exc_info=True)
        # Store error in database
        store_error(job_id, drawing_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))

def load_from_storage(storage_path: str):
    """Load drawing versions from Cloud Storage."""
    storage_client = storage.Client()
    # Assuming storage_path points to a folder with version_a.json and version_b.json
    bucket_name = INPUT_BUCKET
    bucket = storage_client.bucket(bucket_name)
    
    # Load version A
    blob_a = bucket.blob(f"{storage_path}/version_a.json")
    version_a_data = json.loads(blob_a.download_as_text())
    version_a = parse_drawing_json(version_a_data)
    
    # Load version B
    blob_b = bucket.blob(f"{storage_path}/version_b.json")
    version_b_data = json.loads(blob_b.download_as_text())
    version_b = parse_drawing_json(version_b_data)
    
    return version_a, version_b

def store_results(job_id: str, drawing_id: str, changes, start_time: float):
    """Store change results in database."""
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO change_results (drawing_id, job_id, added, removed, moved, summary, processing_time_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            drawing_id,
            job_id,
            json.dumps(changes.added),
            json.dumps(changes.removed),
            json.dumps(changes.moved),
            changes.summary,
            int((time.time() - start_time) * 1000)
        ))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def store_metrics(job_id: str, drawing_id: str, latency_ms: int, changes):
    """Store processing metrics."""
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO processing_metrics (job_id, drawing_id, latency_ms, status, added_count, removed_count, moved_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            job_id,
            drawing_id,
            latency_ms,
            "completed",
            len(changes.added),
            len(changes.removed),
            len(changes.moved)
        ))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def check_anomalies(drawing_id: str, changes):
    """Check for anomalies and store them."""
    # Check for spike in changes
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        # Get previous change count
        cursor.execute("""
            SELECT COUNT(*)
            FROM change_results
            WHERE drawing_id = %s
            AND created_at < NOW() - INTERVAL '1 hour'
        """, (drawing_id,))
        
        previous_count = cursor.fetchone()[0] or 0
        current_count = len(changes.added) + len(changes.removed) + len(changes.moved)
        
        if previous_count > 0 and current_count >= previous_count * 10:
            # Store anomaly
            cursor.execute("""
                INSERT INTO anomalies (drawing_id, anomaly_type, details, severity)
                VALUES (%s, %s, %s, %s)
            """, (
                drawing_id,
                "spike_detected",
                json.dumps({
                    "previous_count": previous_count,
                    "current_count": current_count,
                    "multiplier": current_count / previous_count
                }),
                "high"
            ))
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error checking anomalies: {e}")
    finally:
        cursor.close()
        db.close()

def store_error(job_id: str, drawing_id: str, error_message: str):
    """Store error information."""
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO processing_metrics (job_id, drawing_id, latency_ms, status)
            VALUES (%s, %s, %s, %s)
        """, (job_id, drawing_id, 0, f"error: {error_message[:200]}"))
        
        cursor.execute("""
            INSERT INTO anomalies (drawing_id, anomaly_type, details, severity)
            VALUES (%s, %s, %s, %s)
        """, (drawing_id, "processing_error", json.dumps({"error": error_message}), "high"))
        
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        cursor.close()
        db.close()
```

**Add missing import:**
```python
import base64
```

---

### 2.5 Metrics & Analytics

#### Task: Implement Metrics Collection

The metrics collection is already implemented in the worker (see `store_metrics` function above). Additional aggregation can be added:

**Create `api/utils/metrics_aggregator.py`:**
```python
from api.utils.database import get_db_connection
from datetime import datetime, timedelta
import statistics

def calculate_hourly_stats(hours: int = 24):
    """Calculate hourly statistics for the last N hours."""
    db = get_db_connection()
    cursor = db.cursor()
    
    start_time = datetime.now() - timedelta(hours=hours)
    
    cursor.execute("""
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            SUM(added_count) as total_added,
            SUM(removed_count) as total_removed,
            SUM(moved_count) as total_moved,
            COUNT(*) as total_jobs
        FROM processing_metrics
        WHERE created_at >= %s AND status = 'completed'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour
    """, (start_time,))
    
    return cursor.fetchall()

def calculate_percentiles(hours: int = 24):
    """Calculate P95 and P99 latency percentiles."""
    db = get_db_connection()
    cursor = db.cursor()
    
    start_time = datetime.now() - timedelta(hours=hours)
    
    cursor.execute("""
        SELECT latency_ms
        FROM processing_metrics
        WHERE created_at >= %s AND status = 'completed'
        ORDER BY latency_ms
    """, (start_time,))
    
    latencies = [row[0] for row in cursor.fetchall()]
    
    if not latencies:
        return None, None
    
    p95_index = int(len(latencies) * 0.95)
    p99_index = int(len(latencies) * 0.99)
    
    p95 = latencies[p95_index] if p95_index < len(latencies) else latencies[-1]
    p99 = latencies[p99_index] if p99_index < len(latencies) else latencies[-1]
    
    return p95, p99
```

---

### 2.6 Anomaly Detection

#### Task: Implement Anomaly Detection

The anomaly detection is implemented in the worker's `check_anomalies` function. Additional anomaly types can be added:

**Enhanced Anomaly Detection:**
```python
def detect_missing_uploads():
    """Detect missing or delayed diagram uploads."""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Check for pairs that should have been processed but haven't
    cursor.execute("""
        SELECT drawing_id, created_at
        FROM drawing_pairs
        WHERE status = 'pending'
        AND created_at < NOW() - INTERVAL '2 hours'
    """)
    
    delayed = cursor.fetchall()
    
    for drawing_id, created_at in delayed:
        cursor.execute("""
            INSERT INTO anomalies (drawing_id, anomaly_type, details, severity)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            drawing_id,
            "missing_upload",
            json.dumps({"created_at": created_at.isoformat(), "delay_hours": 2}),
            "medium"
        ))
    
    db.commit()
    cursor.close()
    db.close()
```

---

### 2.7 Data Simulator

#### Task: Create Data Generator

**Create `simulators/data_generator.py`:**
```python
import json
import random
from typing import List, Dict
from google.cloud import storage
import os

def generate_drawing_object(id_prefix: str, index: int, base_x: float = 0, base_y: float = 0) -> Dict:
    """Generate a single drawing object."""
    types = ["wall", "door", "window", "column", "beam"]
    
    return {
        "id": f"{id_prefix}{index}",
        "type": random.choice(types),
        "x": base_x + random.uniform(0, 100),
        "y": base_y + random.uniform(0, 100),
        "width": random.uniform(1, 10),
        "height": random.uniform(1, 10)
    }

def generate_drawing_version(num_objects: int = 10, prefix: str = "A") -> List[Dict]:
    """Generate a complete drawing version."""
    return [generate_drawing_object(prefix, i) for i in range(num_objects)]

def generate_drawing_pair(
    drawing_id: str,
    num_objects_base: int = 10,
    change_probability: float = 0.3
) -> tuple:
    """
    Generate a pair of drawing versions with changes.
    
    Args:
        drawing_id: Unique identifier for the drawing pair
        num_objects_base: Base number of objects
        change_probability: Probability of each object being changed
    
    Returns:
        Tuple of (version_a, version_b) as JSON strings
    """
    version_a = generate_drawing_version(num_objects_base, "A")
    version_b = []
    
    # Copy objects with potential changes
    for obj in version_a:
        if random.random() < change_probability:
            # Change: move the object
            new_obj = obj.copy()
            new_obj["x"] += random.uniform(-5, 5)
            new_obj["y"] += random.uniform(-5, 5)
            version_b.append(new_obj)
        else:
            # No change
            version_b.append(obj.copy())
    
    # Add new objects (additions)
    num_additions = random.randint(0, 3)
    for i in range(num_additions):
        if random.random() < 0.5:
            version_b.append(generate_drawing_object("B", len(version_b)))
    
    # Remove some objects (deletions)
    if random.random() < change_probability and len(version_b) > 2:
        num_removals = random.randint(0, min(2, len(version_b) - 1))
        for _ in range(num_removals):
            version_b.pop(random.randint(0, len(version_b) - 1))
    
    return json.dumps(version_a, indent=2), json.dumps(version_b, indent=2)

def generate_batch(num_pairs: int = 100, output_dir: str = "test_data"):
    """Generate a batch of drawing pairs."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    pairs = []
    for i in range(num_pairs):
        drawing_id = f"drawing_{i:04d}"
        version_a, version_b = generate_drawing_pair(drawing_id)
        
        # Save to files
        with open(f"{output_dir}/{drawing_id}_version_a.json", "w") as f:
            f.write(version_a)
        
        with open(f"{output_dir}/{drawing_id}_version_b.json", "w") as f:
            f.write(version_b)
        
        pairs.append({
            "drawing_id": drawing_id,
            "version_a": version_a,
            "version_b": version_b
        })
    
    return pairs

def upload_to_cloud_storage(pairs: List[Dict], bucket_name: str):
    """Upload generated pairs to Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    for pair in pairs:
        drawing_id = pair["drawing_id"]
        
        # Upload version A
        blob_a = bucket.blob(f"input/{drawing_id}/version_a.json")
        blob_a.upload_from_string(pair["version_a"], content_type="application/json")
        
        # Upload version B
        blob_b = bucket.blob(f"input/{drawing_id}/version_b.json")
        blob_b.upload_from_string(pair["version_b"], content_type="application/json")
    
    print(f"Uploaded {len(pairs)} drawing pairs to gs://{bucket_name}/input/")

if __name__ == "__main__":
    # Generate test data
    pairs = generate_batch(num_pairs=100, output_dir="test_data")
    print(f"Generated {len(pairs)} drawing pairs")
    
    # Optionally upload to Cloud Storage
    # upload_to_cloud_storage(pairs, "buildtrace-input-YOUR-PROJECT-ID")
```

---

### 2.8 Error Handling & Data Quality

#### Task: Implement Error Handling

**Create `api/utils/error_handler.py`:**
```python
import logging
from fastapi import HTTPException
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

class DataQualityError(Exception):
    """Raised when data quality issues are detected."""
    pass

def validate_json_structure(data: Any) -> bool:
    """Validate JSON structure for drawing data."""
    if not isinstance(data, list):
        return False
    
    required_fields = {"id", "type", "x", "y", "width", "height"}
    
    for obj in data:
        if not isinstance(obj, dict):
            return False
        
        if not required_fields.issubset(obj.keys()):
            return False
        
        # Validate value types
        try:
            assert isinstance(obj["id"], str)
            assert isinstance(obj["type"], str)
            float(obj["x"])
            float(obj["y"])
            float(obj["width"])
            float(obj["height"])
        except (ValueError, TypeError, AssertionError):
            return False
    
    return True

def handle_processing_error(error: Exception, drawing_id: str, job_id: str):
    """Handle processing errors and log them."""
    error_details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "drawing_id": drawing_id,
        "job_id": job_id
    }
    
    logger.error(f"Processing error: {json.dumps(error_details)}")
    
    # Store in database
    from api.utils.database import get_db_connection
    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO anomalies (drawing_id, anomaly_type, details, severity)
            VALUES (%s, %s, %s, %s)
        """, (
            drawing_id,
            "processing_error",
            json.dumps(error_details),
            "high"
        ))
        db.commit()
    except Exception as e:
        logger.error(f"Failed to store error: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()
```

---

## Phase 3: Containerization & Deployment

### 3.1 Docker Configuration

#### Task: Create Dockerfiles

**Create `Dockerfile.api`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY workers/processor.py ./workers/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the application
CMD exec uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

**Create `Dockerfile.worker`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY workers/ ./workers/
COPY api/ ./api/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the worker
CMD exec uvicorn workers.main:app --host 0.0.0.0 --port $PORT
```

**Create `requirements.txt`:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
google-cloud-storage==2.10.0
google-cloud-pubsub==2.18.4
google-cloud-tasks==2.14.2
psycopg2-binary==2.9.9
google-cloud-sql-connector[pg8000]==1.4.3
python-dotenv==1.0.0
```

---

### 3.2 Cloud Run Deployment - API Service

#### Task: Build and Deploy API

**Step 1: Build Docker Image**
```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-west2"
export IMAGE_NAME="buildtrace-api"

# Build and push to Artifact Registry
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/$IMAGE_NAME:latest

# Or build locally and push
docker build -f Dockerfile.api -t $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/$IMAGE_NAME:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/$IMAGE_NAME:latest
```

**Step 2: Deploy to Cloud Run**
```bash
gcloud run deploy buildtrace-api \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/$IMAGE_NAME:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --service-account buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,INPUT_BUCKET=buildtrace-input-$PROJECT_ID,OUTPUT_BUCKET=buildtrace-output-$PROJECT_ID,PUBSUB_TOPIC=drawing-processing-tasks,DB_HOST=/cloudsql/$PROJECT_ID:$REGION:buildtrace-db,DB_NAME=buildtrace_db,DB_USER=buildtrace_user,DB_PASS=YOUR_PASSWORD" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:buildtrace-db \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --timeout 300 \
  --port 8080

# Get the service URL
export API_URL=$(gcloud run services describe buildtrace-api --region=$REGION --format="value(status.url)")
echo "API URL: $API_URL"
```

**Via Console:**
1. Navigate to "Cloud Run" > "Create Service"
2. Service name: `buildtrace-api`
3. Region: `us-west2`
4. Container image: Select from Artifact Registry
5. Container port: `8080`
6. Authentication: Allow unauthenticated invocations (for testing)
7. Service account: `buildtrace-service-account@PROJECT_ID.iam.gserviceaccount.com`
8. Connections: Add Cloud SQL instance
9. Environment variables: Add all required variables
10. Memory: 512 MiB
11. CPU: 1
12. Min instances: 0
13. Max instances: 10
14. Concurrency: 80
15. Timeout: 300 seconds
16. Click "CREATE"

---

### 3.3 Cloud Run Deployment - Worker Service

#### Task: Build and Deploy Worker

```bash
# Build worker image
export WORKER_IMAGE="buildtrace-worker"
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/$WORKER_IMAGE:latest -f Dockerfile.worker

# Deploy worker
gcloud run deploy buildtrace-worker \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/$WORKER_IMAGE:latest \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --service-account buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,INPUT_BUCKET=buildtrace-input-$PROJECT_ID,OUTPUT_BUCKET=buildtrace-output-$PROJECT_ID,DB_HOST=/cloudsql/$PROJECT_ID:$REGION:buildtrace-db,DB_NAME=buildtrace_db,DB_USER=buildtrace_user,DB_PASS=YOUR_PASSWORD" \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:buildtrace-db \
  --memory 1Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 20 \
  --concurrency 10 \
  --timeout 900 \
  --port 8080

# Get worker URL
export WORKER_URL=$(gcloud run services describe buildtrace-worker --region=$REGION --format="value(status.url)")
echo "Worker URL: $WORKER_URL"
```

---

### 3.4 Pub/Sub Subscription Configuration

#### Task: Configure Push Subscription

```bash
# Get project number (needed for service account)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Pub/Sub service account permission to invoke Cloud Run
gcloud run services add-iam-policy-binding buildtrace-worker \
  --region=$REGION \
  --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create or update push subscription
gcloud pubsub subscriptions create drawing-processing-workers \
  --topic=drawing-processing-tasks \
  --push-endpoint=$WORKER_URL/process-drawing \
  --ack-deadline=600 \
  --dead-letter-topic=drawing-processing-dlq \
  --max-delivery-attempts=5 \
  --push-auth-service-account=buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com
```

---

### 3.5 IAM & Permissions

Already covered in section 1.7 and 3.4. Verify all permissions are set correctly:

```bash
# Verify service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:buildtrace-service-account@$PROJECT_ID.iam.gserviceaccount.com"
```

---

## Phase 4: Testing & Validation

### 4.1 Local Testing

#### Task: Test Components Locally

**Test Change Detection:**
```python
# test_processor.py
from workers.processor import detect_changes, parse_drawing_json
import json

# Sample data
version_a = [
    {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1},
    {"id": "D1", "type": "door", "x": 4, "y": 2, "width": 1, "height": 2}
]

version_b = [
    {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1},
    {"id": "D1", "type": "door", "x": 6, "y": 2, "width": 1, "height": 2},
    {"id": "W1", "type": "window", "x": 3, "y": 1, "width": 2, "height": 1}
]

va = parse_drawing_json(version_a)
vb = parse_drawing_json(version_b)
result = detect_changes(va, vb)

print(json.dumps(result.dict(), indent=2))
```

**Test API Locally:**
```bash
# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="./buildtrace-key.json"
export PROJECT_ID="your-project-id"
export INPUT_BUCKET="buildtrace-input-your-project-id"
export OUTPUT_BUCKET="buildtrace-output-your-project-id"
export PUBSUB_TOPIC="drawing-processing-tasks"

# Run API
uvicorn api.main:app --reload --port 8000
```

---

### 4.2 Cloud Testing

#### Task: Test Endpoints

**Test POST /process:**
```bash
curl -X POST "$API_URL/process" \
  -H "Content-Type: application/json" \
  -d '{
    "version_pairs": [
      {
        "drawing_id": "test-drawing-1",
        "version_a": "[{\"id\": \"A1\", \"type\": \"wall\", \"x\": 10, \"y\": 5, \"width\": 8, \"height\": 1}]",
        "version_b": "[{\"id\": \"A1\", \"type\": \"wall\", \"x\": 10, \"y\": 5, \"width\": 8, \"height\": 1}, {\"id\": \"W1\", \"type\": \"window\", \"x\": 3, \"y\": 1, \"width\": 2, \"height\": 1}]"
      }
    ]
  }'
```

**Test GET /changes:**
```bash
curl "$API_URL/changes?drawing_id=test-drawing-1"
```

**Test GET /metrics:**
```bash
curl "$API_URL/metrics"
```

**Test GET /health:**
```bash
curl "$API_URL/health"
```

---

### 4.3 Load Testing

#### Task: Generate and Test Large Batch

```python
# Generate 1000 pairs
from simulators.data_generator import generate_batch, upload_to_cloud_storage

pairs = generate_batch(num_pairs=1000)
upload_to_cloud_storage(pairs, "buildtrace-input-YOUR-PROJECT-ID")

# Submit batch via API
import requests
import json

response = requests.post(
    f"{API_URL}/process",
    json={
        "storage_path": "gs://buildtrace-input-YOUR-PROJECT-ID/input/"
    }
)

print(response.json())
```

**Monitor Cloud Run:**
```bash
# Watch service metrics
gcloud run services describe buildtrace-worker --region=$REGION

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-worker" --limit 50
```

---

## Phase 5: Documentation & Delivery

### 5.1 README.md

Create comprehensive README with:
- System architecture diagram (text-based or link to image)
- Data flow explanation
- Scaling strategy
- Fault tolerance approach
- Metrics computation methodology
- Trade-offs and design decisions

### 5.2 Deployment Scripts

**Create `infra/scripts/deploy.sh`:**
```bash
#!/bin/bash
set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-west2"}

echo "Deploying BuildTrace to $PROJECT_ID in $REGION"

# Build and deploy API
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/buildtrace-api:latest
gcloud run deploy buildtrace-api --image $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/buildtrace-api:latest --region=$REGION

# Build and deploy Worker
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/buildtrace-worker:latest -f Dockerfile.worker
gcloud run deploy buildtrace-worker --image $REGION-docker.pkg.dev/$PROJECT_ID/buildtrace-repo/buildtrace-worker:latest --region=$REGION

echo "Deployment complete!"
```

---

## Phase 6: Stretch Goals

### 6.1 BigQuery Integration

Use BigQuery for metrics aggregation ON HOURLY BASIS


### 6.2 Dashboard

Create DASHBOARD FOR MONITORING IN CLOUD  using  custom metrics in  Console with thresholds and alert readiness.

### 6.3 Logging

Ensure structured logging is implemented throughout the application.


### 6.4 Pub/Sub Dead-letter queue 
Implemented but as the genrator didn't create any malformed ones so none when to dlq after retries 


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

# Delete service (cleanup)
gcloud run services delete buildtrace-api --region=$REGION
```

---

This implementation guide provides detailed steps for building the complete BuildTrace system on GCP. Follow each phase sequentially, and adjust configurations based on your specific requirements.

