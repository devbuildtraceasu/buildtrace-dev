# BuildTrace Configuration Guide

Complete guide to configuration management, environment variables, feature flags, and deployment settings.

## Table of Contents

1. [Overview](#overview)
2. [Configuration System](#configuration-system)
3. [Environment Variables](#environment-variables)
4. [Feature Flags](#feature-flags)
5. [Environment-Specific Configs](#environment-specific-configs)
6. [Configuration Validation](#configuration-validation)

## Overview

BuildTrace uses a **hierarchical configuration system** that supports:
- Environment-based configuration
- Feature flags for gradual rollout
- Sensible defaults with override capability
- Validation on startup

**Configuration File**: `config.py`

## Configuration System

### Loading Order

Configuration is loaded in the following priority order (highest to lowest):

1. **Environment Variables** (highest priority)
2. `.env.{ENVIRONMENT}` file (e.g., `.env.production`)
3. `.env` file (fallback)
4. **Default Values** (lowest priority)

### Configuration Class

The `Config` class in `config.py` centralizes all configuration:

```python
from config import config

# Access configuration
print(config.ENVIRONMENT)
print(config.USE_DATABASE)
print(config.OPENAI_API_KEY)
```

## Environment Variables

### Core Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | string | `development` | Environment name (development/production/staging) |
| `DEBUG` | boolean | `true` (dev) / `false` (prod) | Enable debug mode |
| `APP_NAME` | string | `BuildTrace` | Application name |
| `SECRET_KEY` | string | `dev-secret-key...` | Flask secret key (required in production) |
| `HOST` | string | `0.0.0.0` | Bind host |
| `PORT` | integer | `5001` (dev) / `8080` (prod) | Bind port |

### Database Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `USE_DATABASE` | boolean | `false` (dev) / `true` (prod) | Enable database mode |
| `DB_HOST` | string | `localhost` | Database host |
| `DB_PORT` | integer | `5432` | Database port |
| `DB_USER` | string | `buildtrace_user` | Database user |
| `DB_PASS` | string | - | Database password (required if USE_DATABASE=true) |
| `DB_NAME` | string | `buildtrace_db` | Database name |
| `INSTANCE_CONNECTION_NAME` | string | - | Cloud SQL instance connection name |

**Database URL Construction:**
- **Production (Cloud SQL)**: `postgresql://{user}:{pass}@/{db}?host=/cloudsql/{instance}`
- **Development (Local)**: `postgresql://{user}:{pass}@{host}:{port}/{db}`
- **Cloud SQL Proxy**: `postgresql://{user}:{pass}@127.0.0.1:5432/{db}`

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `USE_GCS` | boolean | `false` (dev) / `true` (prod) | Use Google Cloud Storage |
| `GCS_BUCKET_NAME` | string | `buildtrace-storage` | GCS bucket name |
| `GCS_UPLOAD_BUCKET` | string | `buildtrace-drawings-upload` | Upload bucket (if different) |
| `GCS_PROCESSED_BUCKET` | string | `buildtrace-drawings-processed` | Processed files bucket |
| `LOCAL_UPLOAD_PATH` | string | `uploads` | Local upload directory |
| `LOCAL_RESULTS_PATH` | string | `results` | Local results directory |
| `LOCAL_TEMP_PATH` | string | `temp` | Local temp directory |

### OpenAI Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_API_KEY` | string | - | OpenAI API key (required) |
| `OPENAI_MODEL` | string | `gpt-4o` | Model to use |
| `USE_AI_ANALYSIS` | boolean | `true` | Enable AI analysis |

### Processing Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DEFAULT_DPI` | integer | `300` | Default DPI for PDF conversion |
| `MAX_CONTENT_LENGTH` | integer | `73400320` (70MB) | Max upload size in bytes |
| `PROCESSING_TIMEOUT` | integer | `3600` | Processing timeout in seconds |
| `MAX_SYNC_PAGES` | integer | `10` | Max pages for synchronous processing |
| `MEMORY_LIMIT_GB` | float | `10.0` (dev) / `25.0` (prod) | Memory limit for processing |

### Async Processing Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `USE_ASYNC_PROCESSING` | boolean | `false` | Enable async processing |
| `USE_BACKGROUND_PROCESSING` | boolean | `true` | Use background job processor |
| `CLOUD_TASKS_QUEUE` | string | `buildtrace-processing-queue` | Cloud Tasks queue name |
| `CLOUD_TASKS_LOCATION` | string | `us-central1` | Cloud Tasks location |
| `CLOUD_TASKS_PROJECT` | string | `buildtrace` | GCP project for Cloud Tasks |
| `WORKER_URL` | string | - | Worker service URL |

### Security Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ALLOWED_EXTENSIONS` | set | `{'pdf', 'dwg', 'dxf', 'png', 'jpg', 'jpeg'}` | Allowed file extensions |
| `MAX_UPLOAD_SIZE_MB` | integer | `70` | Max upload size in MB |

### Session Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SESSION_LIFETIME_HOURS` | integer | `24` | Session lifetime in hours |
| `CLEANUP_OLD_SESSIONS` | boolean | `true` | Enable automatic cleanup |

## Feature Flags

Feature flags allow gradual rollout and A/B testing:

### Database Feature Flag

```python
USE_DATABASE=true  # Enable database mode
USE_DATABASE=false # Use file-based storage
```

**When Enabled:**
- Sessions stored in PostgreSQL
- Full relational data model
- Better query capabilities
- Scalable architecture

**When Disabled:**
- Sessions stored as JSON files
- Simpler setup for development
- No database required

### GCS Feature Flag

```python
USE_GCS=true   # Use Google Cloud Storage
USE_GCS=false  # Use local file system
```

**When Enabled:**
- Files stored in GCS buckets
- Scalable storage
- Signed URLs for access
- Production-ready

**When Disabled:**
- Files stored locally
- Simpler for development
- No GCS setup required

### Async Processing Flag

```python
USE_ASYNC_PROCESSING=true   # Use background jobs
USE_ASYNC_PROCESSING=false  # Process synchronously
```

**When Enabled:**
- Large files processed in background
- Better user experience
- Requires database
- Uses Cloud Tasks or job processor

**When Disabled:**
- Processing happens in request
- Simpler architecture
- May timeout on large files

### AI Analysis Flag

```python
USE_AI_ANALYSIS=true   # Enable AI analysis
USE_AI_ANALYSIS=false  # Skip AI analysis
```

**When Enabled:**
- GPT-4 analyzes changes
- Generates recommendations
- Requires OpenAI API key

**When Disabled:**
- Skips AI analysis step
- Faster processing
- No API costs

### Firebase Auth Flag

```python
USE_FIREBASE_AUTH=true   # Enable Firebase authentication
USE_FIREBASE_AUTH=false  # No authentication (current)
```

**When Enabled:**
- User authentication required
- User-specific sessions
- Project management

**When Disabled:**
- Public access
- Anonymous sessions
- Simpler setup

## Environment-Specific Configs

### Development Environment

**File**: `.env` or `.env.development`

```bash
ENVIRONMENT=development
DEBUG=true
USE_DATABASE=false
USE_GCS=false
USE_ASYNC_PROCESSING=false
USE_FIREBASE_AUTH=false

# Local database (if using)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=postgres
DB_NAME=buildtrace_db

# Local storage
LOCAL_UPLOAD_PATH=uploads
LOCAL_RESULTS_PATH=results
LOCAL_TEMP_PATH=temp

# OpenAI (required)
OPENAI_API_KEY=sk-...

# Application
HOST=0.0.0.0
PORT=5001
SECRET_KEY=dev-secret-key-change-in-production
```

### Production Environment

**File**: `.env.production` (not committed to git)

```bash
ENVIRONMENT=production
DEBUG=false
USE_DATABASE=true
USE_GCS=true
USE_ASYNC_PROCESSING=true
USE_BACKGROUND_PROCESSING=true

# Cloud SQL
INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres
DB_USER=buildtrace_user
DB_PASS=<encrypted-password>
DB_NAME=buildtrace_db

# Cloud Storage
GCS_BUCKET_NAME=buildtrace-storage
GCS_UPLOAD_BUCKET=buildtrace-drawings-upload
GCS_PROCESSED_BUCKET=buildtrace-drawings-processed

# OpenAI
OPENAI_API_KEY=<encrypted-key>
OPENAI_MODEL=gpt-4o
USE_AI_ANALYSIS=true

# Application
HOST=0.0.0.0
PORT=8080
SECRET_KEY=<strong-random-secret>

# Processing
DEFAULT_DPI=300
MAX_CONTENT_LENGTH=73400320
PROCESSING_TIMEOUT=3600
MEMORY_LIMIT_GB=25.0

# Cloud Tasks (if using)
CLOUD_TASKS_QUEUE=buildtrace-processing-queue
CLOUD_TASKS_LOCATION=us-central1
CLOUD_TASKS_PROJECT=buildtrace
```

### Staging Environment

**File**: `.env.staging`

```bash
ENVIRONMENT=staging
DEBUG=false
USE_DATABASE=true
USE_GCS=true

# Similar to production but with test data
# Use separate Cloud SQL instance
# Use separate GCS bucket
```

## Configuration Validation

### Automatic Validation

The `Config` class validates configuration on import (production only):

```python
if config.IS_PRODUCTION and not config.validate():
    raise RuntimeError("Invalid configuration for production environment")
```

### Validation Rules

**Production Requirements:**
- `OPENAI_API_KEY` must be set
- `DB_PASS` required if `USE_DATABASE=true`
- `GCS_BUCKET_NAME` required if `USE_GCS=true`
- `SECRET_KEY` must not be default value

**Conflicts:**
- `USE_ASYNC_PROCESSING=true` requires `USE_DATABASE=true`
- Cannot use both local and GCS storage simultaneously

### Manual Validation

```python
from config import config

# Check if configuration is valid
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration has errors")
```

## Configuration Access

### In Application Code

```python
from config import config

# Access configuration
if config.USE_DATABASE:
    # Use database
    pass

if config.USE_GCS:
    # Use GCS
    pass
```

### Get Storage Config

```python
storage_config = config.get_storage_config()
# Returns: {'type': 'gcs', 'bucket_name': '...'} or {'type': 'local', 'upload_path': '...'}
```

### Get Data Config

```python
data_config = config.get_data_config()
# Returns: {'type': 'database', 'url': '...'} or {'type': 'file', 'data_dir': '...'}
```

## Environment Variable Examples

### Local Development

```bash
# .env file
ENVIRONMENT=development
DEBUG=true
USE_DATABASE=false
USE_GCS=false
OPENAI_API_KEY=sk-your-key-here
PORT=5001
```

### Production (Cloud Run)

Set via Cloud Run environment variables:

```bash
gcloud run services update buildtrace-overlay \
  --set-env-vars \
    ENVIRONMENT=production,\
    USE_DATABASE=true,\
    USE_GCS=true,\
    INSTANCE_CONNECTION_NAME=buildtrace:us-central1:buildtrace-postgres,\
    DB_USER=buildtrace_user,\
    DB_NAME=buildtrace_db,\
    GCS_BUCKET_NAME=buildtrace-storage,\
    OPENAI_API_KEY=sk-...
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - ENVIRONMENT=development
      - USE_DATABASE=true
      - DB_HOST=postgres
      - DB_USER=buildtrace_user
      - DB_PASS=password
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

## Secrets Management

### Development

Store in `.env` file (not committed to git):
```bash
OPENAI_API_KEY=sk-...
DB_PASS=password
```

### Production (Cloud Run)

Use Cloud Run secrets:
```bash
# Create secret
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Use in Cloud Run
gcloud run services update buildtrace-overlay \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest
```

## Configuration Best Practices

1. **Never Commit Secrets**: Use environment variables or secrets management
2. **Use Feature Flags**: Enable features gradually
3. **Validate on Startup**: Catch configuration errors early
4. **Document Defaults**: Keep defaults documented
5. **Environment-Specific**: Use different configs for dev/staging/prod
6. **Type Safety**: Use appropriate types (boolean, integer, string)
7. **Sensible Defaults**: Provide working defaults for development

## Troubleshooting Configuration

### Check Current Configuration

```python
from config import config
print(config)
# Output: <Config env=development db=False gcs=False async=False>
```

### Verify Environment Variables

```bash
# Check if variable is set
echo $OPENAI_API_KEY

# List all environment variables
env | grep BUILDTRACE
```

### Test Configuration Loading

```python
from config import config
print(f"Environment: {config.ENVIRONMENT}")
print(f"Database: {config.USE_DATABASE}")
print(f"GCS: {config.USE_GCS}")
print(f"OpenAI Key Set: {bool(config.OPENAI_API_KEY)}")
```

---

**Next Steps**: See [SETUP.md](./SETUP.md) for setup instructions or [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment configuration.

