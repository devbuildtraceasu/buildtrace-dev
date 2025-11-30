# BuildTrace GCP Infrastructure

This directory contains all Google Cloud Platform-related files organized for easy navigation and maintenance.

## 📁 Directory Structure

```
gcp/
├── database/           # PostgreSQL Database Layer
│   ├── database.py     # Connection management & Cloud SQL config
│   ├── models.py       # SQLAlchemy models for all tables
│   └── migrations/     # Database schema migrations
│
├── storage/            # Google Cloud Storage Layer
│   └── storage_service.py  # GCS service with local fallback
│
├── infrastructure/     # Background Processing & Utilities
│   ├── job_processor.py        # Background job processor (32GB memory)
│   ├── cloud-sql-proxy        # Cloud SQL proxy binary
│   ├── add_total_time_migration.py  # Database migration utility
│   ├── fix_session_data.py     # Data repair utility
│   └── test_deployment.py      # Deployment testing
│
├── deployment/         # Docker & CI/CD Configuration
│   ├── cloudbuild.yaml     # Cloud Build CI/CD pipeline
│   ├── Dockerfile          # Main application container
│   ├── Dockerfile.full     # Full feature container
│   └── docker-compose.yml  # Local development setup
│
├── scripts/            # Setup & Deployment Scripts
│   ├── setup_gcp_infrastructure.sh  # GCP infrastructure setup
│   ├── setup_database.sh           # Database initialization
│   ├── setup_secrets.sh            # Secrets configuration
│   ├── deploy-branch.sh            # Branch-specific deployment script
│   ├── complete_setup.sh           # Complete environment setup
│   ├── fix_database_setup.sh       # Database repair script
│   └── start-local.sh              # Local development startup
│
└── docs/              # GCP-Specific Documentation
    ├── CLOUD_RUN_DEPLOYMENT.md     # Cloud Run deployment guide
    ├── DATABASE_SETUP_GUIDE.md     # Database setup instructions
    ├── DEPLOYMENT_GUIDE.md         # General deployment guide
    └── SETUP_STATUS.md             # Current setup status
```

## 🏗️ Current Infrastructure

### Production Deployment
- **Project**: `buildtrace`
- **Region**: `us-central1`
- **Environment**: Production-ready with auto-scaling

### Services Deployed
1. **buildtrace-overlay** (Main Web App)
   - 4GB memory, 2 CPU
   - Handles web requests and user interface
   - Connected to Cloud SQL and GCS

2. **buildtrace-job-processor** (Background Jobs)
   - 32GB memory, 4 CPU
   - Processes heavy image analysis tasks
   - Async job processing with database storage

### Infrastructure Components
- **Database**: Cloud SQL PostgreSQL (`buildtrace:us-central1:buildtrace-postgres`)
- **Storage**: Cloud Storage bucket (`buildtrace-storage`)
- **Build**: Cloud Build with Artifact Registry
- **Compute**: Cloud Run with auto-scaling

## 🚀 Quick Start

### Local Development
```bash
# Start local development environment
./gcp/scripts/start-local.sh
```

### Database Access
```bash
# Connect to Cloud SQL database
./gcp/infrastructure/cloud-sql-proxy buildtrace:us-central1:buildtrace-postgres &
```

### Cloud Deployment

#### Prerequisites
1. **Ensure you have a `.env` file in the project root** with your configuration:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   # ... other environment variables
   ```

2. **Authenticate with Google Cloud:**
   ```bash
   # Login to Google Cloud
   gcloud auth login

   # Set the correct project
   gcloud config set project buildtrace

   # Configure Docker authentication (for manual deployment)
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

#### Deployment Options

**Option 1: Cloud Build (Recommended)**
```bash
# Build and deploy using Cloud Build - no local Docker required
gcloud builds submit --config=gcp/deployment/cloudbuild.yaml .
```

**Option 2: Manual Deployment**
```bash
# Deploy using local Docker build + push
./gcp/scripts/deploy-branch.sh
```

#### What Gets Deployed
- **Web App**: `buildtrace-overlay` (4GB memory, 2 CPU)
- **Job Processor**: `buildtrace-job-processor` (32GB memory, 4 CPU)
- **Database**: Connected to Cloud SQL PostgreSQL
- **Storage**: Connected to Cloud Storage bucket

#### Post-Deployment
- **Web App URL**: `https://buildtrace-overlay-[hash]-uc.a.run.app`
- **Check Status**: Use `/health` endpoint
- **View Logs**: See monitoring section below

## 📊 Monitoring & Debugging

### Check Service Status
- **Web App**: https://buildtrace-overlay-[hash]-uc.a.run.app
- **Health Check**: `/health` endpoint
- **Debug Info**: `/api/debug/session/<session_id>` (database mode only)

### Logs Access
```bash
# View application logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-overlay" --limit=50

# View job processor logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=buildtrace-job-processor" --limit=50
```

## 🔧 Configuration

### Environment Variables (Production)
- `ENVIRONMENT=production`
- `DB_USER=buildtrace_user`
- `DB_NAME=buildtrace_db`
- `GCS_BUCKET_NAME=buildtrace-storage`
- `INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres`

### Security
- Database credentials stored as encrypted environment variables
- OpenAI API key configured in Cloud Run
- GCS access via service account authentication

## 📈 Scaling Configuration

### Auto-scaling Settings
- **Web App**: 0-10 instances (scales based on traffic)
- **Job Processor**: 1-3 instances (always warm for immediate processing)
- **Timeout**: 5 minutes for web, 60 minutes for jobs

### Resource Allocation
- **Memory**: 4GB web app, 32GB job processor
- **CPU**: 2 cores web app, 4 cores job processor
- **Disk**: Ephemeral (stateless design)

## 🔍 Troubleshooting

### Common Deployment Issues

#### Authentication Errors
```bash
# Error: "Unauthenticated request" or "Reauthentication failed"
# Solution: Re-authenticate with Google Cloud
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### Missing .env File
```bash
# Error: "OPENAI_API_KEY not found in .env!"
# Solution: Ensure .env file exists in project root with required variables
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
# ... other variables
EOF
```

#### Docker Build Issues
```bash
# Error: "open Dockerfile: no such file or directory"
# Solution: Use the correct Dockerfile path (fixed in current version)
docker build -f gcp/deployment/Dockerfile -t buildtrace-overlay .
```

#### Cloud Build Permission Issues
```bash
# Error: Permission denied for Artifact Registry
# Solution: Ensure Cloud Build service account has proper permissions
gcloud projects add-iam-policy-binding buildtrace \
  --member="serviceAccount:123644909590@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

### Common Runtime Issues
1. **Database Connection**: Check Cloud SQL proxy and credentials
2. **Storage Access**: Verify GCS bucket permissions
3. **Memory Issues**: Monitor job processor memory usage (32GB limit)
4. **Timeouts**: Check processing time vs timeout limits

### Quick Deployment Verification
```bash
# Check if services are running
gcloud run services list --region=us-central1

# Test the web app
curl https://buildtrace-overlay-[hash]-uc.a.run.app/health

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### Debug Commands
```bash
# Test database connection
python -c "from gcp.database import get_db; print('DB connection OK')"

# Test storage access
python -c "from gcp.storage import storage_service; print(storage_service.list_files()[:5])"

# Check deployment status
gcloud run services describe buildtrace-overlay --region=us-central1
```

## 📚 Development Workflow

1. **Local Development**: Use `start-local.sh` for local testing
2. **Database Changes**: Add migrations to `database/migrations/`
3. **Storage Updates**: Modify `storage/storage_service.py`
4. **Deployment**: Use `scripts/deploy-branch.sh` for production
5. **Monitoring**: Check Cloud Run logs and metrics

## 🛡️ Security Best Practices

- ✅ Encrypted database credentials
- ✅ Service account authentication for GCS
- ✅ Private container registry (Artifact Registry)
- ✅ HTTPS-only communication
- ✅ No public database access (Cloud SQL Private IP)

---

For specific setup instructions, see the documentation in `docs/` directory.