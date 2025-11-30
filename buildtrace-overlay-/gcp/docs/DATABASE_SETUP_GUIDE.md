# BuildTrace Database & Storage Setup Guide

## Overview
This guide will help you set up PostgreSQL on Cloud SQL and Google Cloud Storage for the BuildTrace application. The new architecture includes:
- **Project Management**: Organize drawings by projects
- **Version Tracking**: Automatically compare with previous versions of the same drawing
- **Persistent Storage**: All data stored in PostgreSQL and files in GCS

## Architecture Changes

### New Data Model
```
User → Projects → Drawing Versions
              ↘
               Sessions → Comparisons → Analysis Results
```

- **Users**: Can have multiple projects
- **Projects**: Container for organizing drawings (default project created automatically)
- **Drawing Versions**: Track version history of each drawing (A-101 v1, v2, v3...)
- **Sessions**: Individual upload/comparison sessions that can be moved between projects

## Step 1: Set Up GCP Resources

### Option A: Automated Setup
```bash
# Make the script executable
chmod +x setup_gcp_infrastructure.sh

# Run the setup script
./setup_gcp_infrastructure.sh
```

### Option B: Manual Setup

#### 1.1 Create Cloud SQL Instance
```bash
gcloud sql instances create buildtrace-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --network=default \
    --storage-type=SSD \
    --storage-size=10GB
```

#### 1.2 Create Database and User
```bash
# Create database
gcloud sql databases create buildtrace_db --instance=buildtrace-postgres

# Create user (you'll be prompted for password)
gcloud sql users create buildtrace_user --instance=buildtrace-postgres
```

#### 1.3 Create Cloud Storage Bucket
```bash
gsutil mb -p buildtrace -c STANDARD -l us-central1 gs://buildtrace-storage/
```

## Step 2: Configure Local Development

### 2.1 Install Cloud SQL Proxy
```bash
# Download Cloud SQL Proxy
curl -o cloud-sql-proxy https://dl.google.com/cloudsql/cloud_sql_proxy.darwin.amd64
chmod +x cloud-sql-proxy

# Start proxy (run in separate terminal)
./cloud-sql-proxy --instances=buildtrace:us-central1:buildtrace-postgres=tcp:5432
```

### 2.2 Set Up Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your values
# Important variables to set:
# - DB_PASS: Password you set for buildtrace_user
# - OPENAI_API_KEY: Your OpenAI API key
# - GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (for local dev)
```

### 2.3 Create Service Account (for local development)
```bash
# Create service account
gcloud iam service-accounts create buildtrace-dev \
    --display-name="BuildTrace Development"

# Download credentials
gcloud iam service-accounts keys create \
    ./credentials/service-account.json \
    --iam-account=buildtrace-dev@buildtrace.iam.gserviceaccount.com

# Grant necessary permissions
gcloud projects add-iam-policy-binding buildtrace \
    --member="serviceAccount:buildtrace-dev@buildtrace.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding buildtrace \
    --member="serviceAccount:buildtrace-dev@buildtrace.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

## Step 3: Initialize Database

### 3.1 Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3.2 Create Database Tables
```bash
# Initialize database schema
python migrations/init_database.py

# Or to reset everything (drops all tables first)
python migrations/init_database.py --reset
```

## Step 4: Test the Setup

### 4.1 Test Database Connection
```python
# Run Python to test
python
>>> from database import db_manager
>>> with db_manager.get_session() as session:
...     result = session.execute("SELECT 1")
...     print("Database connected!")
```

### 4.2 Test Cloud Storage
```python
>>> from services.storage_service import storage_service
>>> test_content = b"Hello, Cloud Storage!"
>>> path = storage_service.upload_file(test_content, "test/hello.txt")
>>> print(f"Uploaded to: {path}")
>>> downloaded = storage_service.download_file("test/hello.txt")
>>> print(f"Downloaded: {downloaded}")
```

## Step 5: Update Application Code

The application needs to be updated to use the new database and storage services. Key changes:

1. **File Uploads**: Now stored in Cloud Storage instead of local filesystem
2. **Session Management**: Stored in database with project association
3. **Drawing Versions**: Automatic version tracking when same drawing uploaded
4. **Comparison Logic**: Can now compare with previous versions automatically

## Step 6: Production Deployment

### 6.1 Update Cloud Run Service
```bash
# Set environment variables for Cloud Run
gcloud run services update buildtrace-app \
    --set-env-vars="ENVIRONMENT=production,DB_USER=buildtrace_user,DB_NAME=buildtrace_db,GCS_BUCKET_NAME=buildtrace-storage" \
    --add-cloudsql-instances=buildtrace:us-central1:buildtrace-postgres
```

### 6.2 Store Secrets in Secret Manager
```bash
# Store database password
echo -n "your_db_password" | gcloud secrets create db-password --data-file=-

# Store OpenAI API key
echo -n "your_openai_key" | gcloud secrets create openai-api-key --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
```

## Usage Examples

### Working with Projects
```python
from database import get_db_session
from services.project_service import ProjectService

with get_db_session() as db:
    project_service = ProjectService(db)

    # Get or create user
    user = project_service.get_or_create_user("user@example.com")

    # Create a new project
    project = project_service.create_project(
        user_id=user.id,
        name="Office Building Renovation",
        client_name="ABC Corp",
        location="New York, NY"
    )

    # Move existing session to project
    project_service.move_session_to_project(session_id, project.id)
```

### Automatic Version Comparison
When uploading new drawings to a project, the system will:
1. Check if drawings with the same name exist in the project
2. Create new version entries
3. Automatically set up comparisons with the previous version
4. No more manual "old vs new" selection needed!

## Troubleshooting

### Database Connection Issues
```bash
# Check Cloud SQL Proxy is running
ps aux | grep cloud-sql-proxy

# Test connection directly
psql -h localhost -U buildtrace_user -d buildtrace_db
```

### Storage Permission Issues
```bash
# Verify bucket exists
gsutil ls gs://buildtrace-storage/

# Check service account permissions
gcloud projects get-iam-policy buildtrace
```

### Local Development Fallback
If Cloud services are unavailable during development:
- Database: Install local PostgreSQL
- Storage: Files will fallback to ./uploads directory

## Next Steps

1. **Update app.py** to use the new services
2. **Add authentication** for user management
3. **Create project management UI** for users to organize their drawings
4. **Implement automatic version comparison** workflow

## Benefits of This Architecture

1. **Scalability**: Cloud SQL and GCS can handle growing data
2. **Reliability**: Managed services with automatic backups
3. **Version Control**: Track all drawing changes over time
4. **Organization**: Projects provide logical grouping
5. **Cost-Effective**: Pay only for what you use
6. **Performance**: CDN-ready file serving from GCS