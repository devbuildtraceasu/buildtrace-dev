# BuildTrace Storage Documentation

Complete guide to storage architecture, file management, and access patterns.

## Table of Contents

1. [Overview](#overview)
2. [Storage Modes](#storage-modes)
3. [File Organization](#file-organization)
4. [Storage Service](#storage-service)
5. [Access Patterns](#access-patterns)
6. [Performance](#performance)

## Overview

BuildTrace uses a **unified storage abstraction** that supports:
- **Local Storage**: File system (development)
- **Google Cloud Storage**: Object storage (production)
- **Automatic Fallback**: Seamless switching between modes

**Storage Service**: `gcp/storage/storage_service.py`

## Storage Modes

### Local Storage Mode

**When Used**: Development or when `USE_GCS=false`

**Configuration:**
```bash
USE_GCS=false
LOCAL_UPLOAD_PATH=uploads
LOCAL_RESULTS_PATH=results
LOCAL_TEMP_PATH=temp
```

**Storage Location:**
```
project-root/
├── uploads/
│   └── sessions/
│       └── {session_id}/
│           ├── uploads/
│           └── results/
├── results/
└── temp/
```

**Advantages:**
- No cloud setup required
- Fast local access
- Easy debugging
- No costs

**Limitations:**
- Not scalable
- Not persistent across deployments
- No sharing between instances

### Google Cloud Storage Mode

**When Used**: Production or when `USE_GCS=true`

**Configuration:**
```bash
USE_GCS=true
GCS_BUCKET_NAME=buildtrace-storage
GCS_UPLOAD_BUCKET=buildtrace-drawings-upload
GCS_PROCESSED_BUCKET=buildtrace-drawings-processed
```

**Storage Location:**
```
gs://buildtrace-storage/
├── sessions/
│   └── {session_id}/
│       ├── uploads/
│       └── results/
└── drawings/
```

**Advantages:**
- Scalable
- Persistent
- Shared across instances
- Production-ready
- Signed URLs for secure access

**Limitations:**
- Requires GCS setup
- Network latency
- Storage costs

## File Organization

### Directory Structure

```
sessions/
└── {session_id}/
    ├── uploads/
    │   ├── old_drawings.pdf
    │   └── new_drawings.pdf
    └── results/
        ├── {drawing_name}/
        │   ├── {drawing_name}_old.png
        │   ├── {drawing_name}_new.png
        │   ├── {drawing_name}_overlay.png
        │   └── change_analysis_{drawing_name}.json
        └── summary.json
```

### File Naming Conventions

**Uploaded Files:**
- Original filename preserved in metadata
- Stored as: `{original_filename}` or `{secure_filename}`

**Processed Files:**
- Drawing images: `{drawing_name}_old.png`, `{drawing_name}_new.png`
- Overlays: `{drawing_name}_overlay.png`
- Analysis: `change_analysis_{drawing_name}.json`

**Session Files:**
- Session metadata: `sessions/{session_id}/metadata.json`
- Results summary: `sessions/{session_id}/results/summary.json`

## Storage Service

### CloudStorageService Class

**Location**: `gcp/storage/storage_service.py`

**Key Methods:**

#### Upload Operations

```python
# Upload file from memory
storage_service.upload_file(
    file_content=file_bytes,
    destination_path="sessions/{session_id}/uploads/file.pdf",
    content_type="application/pdf"
)

# Upload file from local path
storage_service.upload_from_filename(
    local_path="/tmp/file.pdf",
    destination_path="sessions/{session_id}/uploads/file.pdf"
)
```

#### Download Operations

```python
# Download as bytes
content = storage_service.download_file("sessions/{session_id}/file.pdf")

# Download to local file
storage_service.download_to_filename(
    source_path="sessions/{session_id}/file.pdf",
    local_path="/tmp/file.pdf"
)

# Download to file object
with open("/tmp/file.pdf", "wb") as f:
    storage_service.download_to_file("sessions/{session_id}/file.pdf", f)
```

#### File Management

```python
# Check if file exists
exists = storage_service.file_exists("sessions/{session_id}/file.pdf")

# Delete file
success = storage_service.delete_file("sessions/{session_id}/file.pdf")

# List files
files = storage_service.list_files(prefix="sessions/{session_id}/")

# Move/rename file
storage_service.move_file(
    source_path="sessions/{session_id}/old_name.pdf",
    destination_path="sessions/{session_id}/new_name.pdf"
)
```

#### Signed URLs

```python
# Generate signed URL for download
url = storage_service.generate_signed_url(
    path="sessions/{session_id}/file.pdf",
    expiration_minutes=60
)

# Generate signed URL for upload
upload_url = storage_service.generate_signed_upload_url(
    path="sessions/{session_id}/file.pdf",
    expiration_minutes=60,
    content_type="application/pdf"
)
```

### Automatic Fallback

The storage service automatically falls back to local storage if GCS is unavailable:

```python
# In development, automatically uses local storage
# In production, uses GCS with local fallback on error
storage_service.upload_file(...)  # Works in both modes
```

## Access Patterns

### Upload Pattern

```python
# 1. Receive file upload
file = request.files['file']

# 2. Generate storage path
session_id = generate_session_id()
storage_path = f"sessions/{session_id}/uploads/{file.filename}"

# 3. Upload to storage
storage_service.upload_file(
    file_content=file.read(),
    destination_path=storage_path,
    content_type=file.content_type
)

# 4. Store metadata in database
with get_db_session() as db:
    drawing = Drawing(
        session_id=session_id,
        filename=file.filename,
        storage_path=storage_path
    )
    db.add(drawing)
    db.commit()
```

### Download Pattern

```python
# 1. Get file metadata from database
with get_db_session() as db:
    drawing = db.query(Drawing).filter_by(id=drawing_id).first()
    storage_path = drawing.storage_path

# 2. Generate signed URL (GCS) or local path
if config.USE_GCS:
    url = storage_service.generate_signed_url(storage_path)
else:
    url = f"/api/files/{session_id}/{filename}"

# 3. Return URL to client
return jsonify({"url": url})
```

### Processing Pattern

```python
# 1. Download files to temporary directory
with tempfile.TemporaryDirectory() as temp_dir:
    old_path = os.path.join(temp_dir, "old.pdf")
    new_path = os.path.join(temp_dir, "new.pdf")
    
    storage_service.download_to_filename(old_storage_path, old_path)
    storage_service.download_to_filename(new_storage_path, new_path)
    
    # 2. Process files
    results = complete_drawing_pipeline(old_path, new_path)
    
    # 3. Upload results
    for overlay_path in results['overlays']:
        storage_path = f"sessions/{session_id}/results/{overlay_path}"
        storage_service.upload_from_filename(
            local_path=overlay_path,
            destination_path=storage_path
        )
```

## Performance

### Optimization Strategies

1. **Parallel Uploads**
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(storage_service.upload_file, file, path)
        for file, path in files
    ]
    results = [f.result() for f in futures]
```

2. **Streaming Uploads**
```python
# For large files, use streaming
with open(local_path, 'rb') as f:
    storage_service.upload_file(f, destination_path)
```

3. **Batch Operations**
```python
# List files in batch
files = storage_service.list_files(prefix="sessions/{session_id}/")
```

### Caching

**Local Cache:**
- Cache file metadata
- Cache signed URLs (with expiration)
- Cache file existence checks

**CDN Integration** (Future):
- Use CDN for static assets
- Cache processed images
- Reduce GCS requests

## Security

### Access Control

**Local Storage:**
- File system permissions
- Directory isolation
- Secure filename handling

**GCS Storage:**
- IAM-based access control
- Signed URLs for temporary access
- Bucket-level permissions
- Object-level ACLs (if needed)

### Signed URLs

**Download URLs:**
- Temporary access (default: 60 minutes)
- Expiration time configurable
- HTTPS only

**Upload URLs:**
- Direct client uploads
- Temporary access
- Content type validation

### File Validation

```python
# Validate file type
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'png', 'jpg', 'jpeg'}
if not file.filename.endswith(tuple(ALLOWED_EXTENSIONS)):
    raise ValueError("Invalid file type")

# Validate file size
MAX_SIZE = config.MAX_CONTENT_LENGTH
if len(file_content) > MAX_SIZE:
    raise ValueError("File too large")

# Sanitize filename
filename = secure_filename(file.filename)
```

## Lifecycle Management

### GCS Lifecycle Policies

**Automatic Cleanup:**
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["sessions/"]
        }
      }
    ]
  }
}
```

**Archive Old Files:**
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      }
    ]
  }
}
```

### Manual Cleanup

```python
# Clean up old sessions
from datetime import datetime, timedelta

cutoff_date = datetime.utcnow() - timedelta(days=90)
old_sessions = db.query(Session).filter(
    Session.created_at < cutoff_date
).all()

for session in old_sessions:
    # Delete files
    files = storage_service.list_files(prefix=f"sessions/{session.id}/")
    for file_path in files:
        storage_service.delete_file(file_path)
    
    # Delete database records
    db.delete(session)
```

## Monitoring

### Storage Metrics

**GCS Metrics:**
- Storage usage
- Request counts
- Error rates
- Bandwidth usage

**Local Storage:**
- Disk usage
- File counts
- Directory sizes

### Alerts

**Set Up Alerts For:**
- Storage quota warnings (80%, 90%, 95%)
- High error rates
- Unusual access patterns
- Cost thresholds

---

**Next Steps**: See [CONFIGURATION.md](./CONFIGURATION.md) for storage configuration or [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for storage issues.

