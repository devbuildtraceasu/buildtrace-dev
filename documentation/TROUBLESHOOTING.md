# BuildTrace Troubleshooting Guide

Comprehensive troubleshooting guide for common issues, errors, and solutions.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Setup Issues](#setup-issues)
3. [Database Issues](#database-issues)
4. [Storage Issues](#storage-issues)
5. [Processing Issues](#processing-issues)
6. [API Issues](#api-issues)
7. [Deployment Issues](#deployment-issues)
8. [Performance Issues](#performance-issues)

## Quick Diagnostics

### Health Check

```bash
# Check application health
curl http://localhost:5001/health

# Expected response:
# {"status": "healthy", "environment": "development", ...}
```

### Configuration Check

```python
from config import config
print(f"Environment: {config.ENVIRONMENT}")
print(f"Database: {config.USE_DATABASE}")
print(f"GCS: {config.USE_GCS}")
print(f"OpenAI Key: {'Set' if config.OPENAI_API_KEY else 'Missing'}")
```

### Logs Check

```bash
# Local development
tail -f app.log

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

## Setup Issues

### Issue: Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'cv2'
ImportError: cannot import name 'Config' from 'config'
```

**Solutions:**

1. **Activate Virtual Environment:**
```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate    # Windows
```

2. **Reinstall Dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Check Python Version:**
```bash
python --version  # Should be 3.11+
```

### Issue: Tesseract Not Found

**Symptoms:**
```
TesseractNotFoundError: tesseract is not installed
```

**Solutions:**

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH

**Verify Installation:**
```bash
tesseract --version
```

### Issue: Poppler Not Found

**Symptoms:**
```
PDFInfoNotInstalledError: Unable to get page count
```

**Solutions:**

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
- Download from: https://github.com/oschwartz10612/poppler-windows/releases

### Issue: Port Already in Use

**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solutions:**

1. **Change Port:**
```bash
# In .env file
PORT=5002
```

2. **Find and Kill Process:**
```bash
# macOS/Linux
lsof -ti:5001 | xargs kill -9

# Windows
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

### Issue: Missing .env File

**Symptoms:**
```
KeyError: 'OPENAI_API_KEY'
```

**Solutions:**

1. **Create .env File:**
```bash
cp .env.example .env
# Edit .env with your values
```

2. **Set Environment Variables:**
```bash
export OPENAI_API_KEY=sk-...
export ENVIRONMENT=development
```

## Database Issues

### Issue: Database Connection Failed

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
psycopg2.OperationalError: connection refused
```

**Solutions:**

1. **Check PostgreSQL is Running:**
```bash
# macOS/Linux
pg_isready

# Check status
sudo systemctl status postgresql  # Linux
brew services list | grep postgres  # macOS
```

2. **Verify Connection String:**
```python
from config import config
print(config.DATABASE_URL)
```

3. **Test Connection:**
```bash
psql -h localhost -U buildtrace_user -d buildtrace_db
```

4. **Check Firewall:**
```bash
# Allow PostgreSQL port
sudo ufw allow 5432
```

### Issue: Authentication Failed

**Symptoms:**
```
psycopg2.OperationalError: password authentication failed
```

**Solutions:**

1. **Reset Password:**
```bash
# Connect as postgres user
psql -U postgres

# Change password
ALTER USER buildtrace_user WITH PASSWORD 'new_password';
```

2. **Update .env:**
```bash
DB_PASS=new_password
```

### Issue: Database Does Not Exist

**Symptoms:**
```
psycopg2.OperationalError: database "buildtrace_db" does not exist
```

**Solutions:**

1. **Create Database:**
```bash
createdb buildtrace_db

# Or using psql
psql -U postgres
CREATE DATABASE buildtrace_db;
```

2. **Initialize Schema:**
```python
from gcp.database import init_db
init_db()
```

### Issue: Cloud SQL Connection Failed

**Symptoms:**
```
Cloud SQL connection failed: connection timeout
```

**Solutions:**

1. **Verify Instance Name:**
```bash
gcloud sql instances list
```

2. **Check Cloud SQL Proxy:**
```bash
# Start proxy
./cloud_sql_proxy -instances=buildtrace:us-central1:buildtrace-postgres=tcp:5432

# In another terminal, test connection
psql -h 127.0.0.1 -U buildtrace_user -d buildtrace_db
```

3. **Verify Service Account Permissions:**
```bash
gcloud projects get-iam-policy buildtrace \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:*"
```

## Storage Issues

### Issue: GCS Access Denied

**Symptoms:**
```
google.api_core.exceptions.Forbidden: 403 Access Denied
```

**Solutions:**

1. **Verify Service Account:**
```bash
gcloud auth application-default login
```

2. **Check Bucket Permissions:**
```bash
gsutil iam get gs://buildtrace-storage
```

3. **Grant Permissions:**
```bash
gsutil iam ch serviceAccount:SERVICE_ACCOUNT:objectAdmin gs://buildtrace-storage
```

### Issue: Local Storage Path Not Found

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'uploads/...'
```

**Solutions:**

1. **Create Directories:**
```bash
mkdir -p uploads results temp
```

2. **Check Permissions:**
```bash
chmod 755 uploads results temp
```

### Issue: File Upload Fails

**Symptoms:**
```
413 Request Entity Too Large
```

**Solutions:**

1. **Increase Upload Limit:**
```bash
# In .env
MAX_CONTENT_LENGTH=104857600  # 100MB
```

2. **Check Nginx/Apache Limits** (if using reverse proxy):
```nginx
client_max_body_size 100M;
```

## Processing Issues

### Issue: No Features Detected

**Symptoms:**
```
ValueError: Need at least 4 matches to estimate transformation
```

**Solutions:**

1. **Increase Image Quality:**
```python
# Use higher DPI
complete_drawing_pipeline(..., dpi=600)
```

2. **Check Image Quality:**
```python
# Verify images are not corrupted
import cv2
img = cv2.imread('image.png')
print(img.shape)  # Should not be None
```

3. **Preprocess Images:**
```python
# Enhance contrast
img = cv2.convertScaleAbs(img, alpha=1.5, beta=30)
```

### Issue: Alignment Failed

**Symptoms:**
```
Alignment score too low: 0.2
```

**Solutions:**

1. **Check if Correct Drawings Matched:**
```python
# Verify drawing names match
print(f"Old: {old_drawing_name}, New: {new_drawing_name}")
```

2. **Try Different DPI:**
```python
# Higher DPI may improve feature detection
complete_drawing_pipeline(..., dpi=600)
```

3. **Manual Alignment:**
```python
# Use manual transformation if automatic fails
# (Feature to be implemented)
```

### Issue: OpenAI API Error

**Symptoms:**
```
openai.error.RateLimitError: Rate limit exceeded
openai.error.APIError: Invalid API key
```

**Solutions:**

1. **Check API Key:**
```bash
echo $OPENAI_API_KEY
# Should start with sk-
```

2. **Verify API Key:**
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Test with simple request
```

3. **Handle Rate Limits:**
```python
# Add retry logic
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_openai():
    # API call
    pass
```

### Issue: Processing Timeout

**Symptoms:**
```
TimeoutError: Processing exceeded timeout
```

**Solutions:**

1. **Increase Timeout:**
```bash
# In .env
PROCESSING_TIMEOUT=7200  # 2 hours
```

2. **Use Async Processing:**
```bash
USE_ASYNC_PROCESSING=true
USE_BACKGROUND_PROCESSING=true
```

3. **Process in Chunks:**
```python
# Use chunked processor for large files
from chunked_processor import process_documents
results = process_documents(old_file, new_file)
```

## API Issues

### Issue: 404 Not Found

**Symptoms:**
```
404 Not Found: The requested URL was not found
```

**Solutions:**

1. **Check Route:**
```python
# Verify route exists in app.py
@app.route('/api/endpoint')
```

2. **Check Base URL:**
```bash
# Verify correct base URL
curl http://localhost:5001/health
```

3. **Check Session ID:**
```python
# Verify session exists
from gcp.database import get_db_session
with get_db_session() as db:
    session = db.query(Session).filter_by(id=session_id).first()
```

### Issue: 500 Internal Server Error

**Symptoms:**
```
500 Internal Server Error
```

**Solutions:**

1. **Check Logs:**
```bash
# Local
tail -f app.log

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

2. **Enable Debug Mode:**
```bash
# In .env
DEBUG=true
```

3. **Check Error Details:**
```python
# Add error handling
try:
    # Code
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
```

### Issue: CORS Error

**Symptoms:**
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Solutions:**

1. **Add CORS Headers:**
```python
from flask_cors import CORS
CORS(app)
```

2. **Configure CORS:**
```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourdomain.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"]
    }
})
```

## Deployment Issues

### Issue: Docker Build Fails

**Symptoms:**
```
ERROR: failed to solve: process "/bin/sh -c pip install..." did not complete successfully
```

**Solutions:**

1. **Check Dockerfile:**
```bash
# Verify Dockerfile syntax
docker build -f gcp/deployment/Dockerfile -t test .
```

2. **Check Dependencies:**
```bash
# Verify requirements.txt is valid
pip install -r requirements.txt
```

3. **Clear Docker Cache:**
```bash
docker build --no-cache -f gcp/deployment/Dockerfile -t buildtrace .
```

### Issue: Cloud Run Deployment Fails

**Symptoms:**
```
ERROR: (gcloud.run.deploy) Revision failed with message: Container failed to start
```

**Solutions:**

1. **Check Logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit=100
```

2. **Verify Environment Variables:**
```bash
gcloud run services describe buildtrace-overlay \
    --region=us-central1 \
    --format="value(spec.template.spec.containers[0].env)"
```

3. **Test Locally:**
```bash
docker run -e ENVIRONMENT=production ...
```

### Issue: Cloud Build Fails

**Symptoms:**
```
ERROR: build step "gcr.io/cloud-builders/docker" failed
```

**Solutions:**

1. **Check Cloud Build Logs:**
```bash
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

2. **Verify Permissions:**
```bash
gcloud projects get-iam-policy buildtrace
```

3. **Check Artifact Registry:**
```bash
gcloud artifacts repositories list
```

## Performance Issues

### Issue: Slow Processing

**Symptoms:**
- Processing takes > 5 minutes per drawing
- High CPU usage
- Memory usage spikes

**Solutions:**

1. **Optimize DPI:**
```python
# Lower DPI for faster processing (trade-off: quality)
complete_drawing_pipeline(..., dpi=200)
```

2. **Use Async Processing:**
```bash
USE_ASYNC_PROCESSING=true
```

3. **Increase Resources:**
```bash
# Cloud Run
gcloud run services update buildtrace-overlay \
    --memory 8Gi \
    --cpu 4
```

4. **Cache Results:**
```python
# Cache feature descriptors
# Cache converted images
```

### Issue: High Memory Usage

**Symptoms:**
- Out of memory errors
- Container killed

**Solutions:**

1. **Increase Memory:**
```bash
# Cloud Run
gcloud run services update buildtrace-overlay \
    --memory 8Gi
```

2. **Process in Chunks:**
```python
from chunked_processor import process_documents
```

3. **Optimize Image Processing:**
```python
# Resize images before processing
img = cv2.resize(img, (width//2, height//2))
```

### Issue: Database Slow Queries

**Symptoms:**
- Slow API responses
- Database connection timeouts

**Solutions:**

1. **Add Indexes:**
```sql
CREATE INDEX idx_session_status ON sessions(status);
CREATE INDEX idx_drawing_name ON drawings(drawing_name);
```

2. **Optimize Queries:**
```python
# Use eager loading
session = db.query(Session)\
    .options(joinedload(Session.drawings))\
    .filter_by(id=session_id)\
    .first()
```

3. **Connection Pooling:**
```python
# Already configured in database.py
# Adjust pool size if needed
```

## Getting Help

### Debug Mode

Enable debug mode for detailed error messages:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Logging

Add detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

### Support Resources

1. **Check Documentation**: Review relevant docs
2. **Check Logs**: Always check logs first
3. **Reproduce Issue**: Create minimal reproduction
4. **Check GitHub Issues**: Search for similar issues

---

**Next Steps**: See [DEVELOPMENT.md](./DEVELOPMENT.md) for development workflow or [API.md](./API.md) for API usage.

