# BuildTrace API Documentation

Complete API reference for BuildTrace endpoints, request/response formats, and usage examples.

## Table of Contents

1. [Base URL](#base-url)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Core Endpoints](#core-endpoints)
5. [Session Endpoints](#session-endpoints)
6. [Processing Endpoints](#processing-endpoints)
7. [Chat Endpoints](#chat-endpoints)
8. [File Endpoints](#file-endpoints)
9. [WebSocket Events](#websocket-events)

## Base URL

**Local Development:**
```
http://localhost:5001
```

**Production:**
```
https://buildtrace-overlay-[hash]-uc.a.run.app
```

## Authentication

Currently, BuildTrace does not require authentication. All endpoints are publicly accessible.

**Future**: Firebase Authentication will be integrated (feature flag: `USE_FIREBASE_AUTH`).

## Error Handling

### Error Response Format

```json
{
  "error": "Error message description",
  "code": "ERROR_CODE",
  "details": {}
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 500 | Internal Server Error |

### Common Error Codes

- `VALIDATION_ERROR`: Invalid input data
- `FILE_TOO_LARGE`: Upload exceeds size limit
- `INVALID_FILE_TYPE`: Unsupported file format
- `SESSION_NOT_FOUND`: Session ID doesn't exist
- `PROCESSING_FAILED`: Pipeline processing error
- `STORAGE_ERROR`: Storage operation failed
- `DATABASE_ERROR`: Database operation failed

## Core Endpoints

### Health Check

**GET** `/health`

Check application health and status.

**Response:**
```json
{
  "status": "healthy",
  "environment": "development",
  "database": "connected",
  "storage": "local",
  "version": "1.0.0"
}
```

**Example:**
```bash
curl http://localhost:5001/health
```

### Root

**GET** `/`

Returns the main web interface (HTML page).

**Response:** HTML content

---

## Session Endpoints

### Create Session

**POST** `/upload`

Upload old and new drawing files to create a new session.

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `old_file`: File (PDF, DWG, DXF, PNG, JPG)
  - `new_file`: File (PDF, DWG, DXF, PNG, JPG)

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "uploaded",
  "old_filename": "old_drawings.pdf",
  "new_filename": "new_drawings.pdf",
  "old_size": 5242880,
  "new_size": 6291456,
  "message": "Files uploaded successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:5001/upload \
  -F "old_file=@old_drawings.pdf" \
  -F "new_file=@new_drawings.pdf"
```

**Error Responses:**
- `400`: Invalid file type or size
- `413`: File too large
- `500`: Upload failed

### Get Session Status

**GET** `/api/sessions/<session_id>`

Get session information and status.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "total_time": 45.2,
  "old_filename": "old_drawings.pdf",
  "new_filename": "new_drawings.pdf",
  "overlays_created": 5,
  "analyses_completed": 5
}
```

**Example:**
```bash
curl http://localhost:5001/api/sessions/550e8400-e29b-41d4-a716-446655440000
```

### List Recent Sessions

**GET** `/api/sessions/recent`

Get list of recent sessions.

**Query Parameters:**
- `limit`: Number of sessions to return (default: 10, max: 50)

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "overlays_created": 5
    }
  ],
  "total": 10
}
```

**Example:**
```bash
curl http://localhost:5001/api/sessions/recent?limit=20
```

### Delete Session

**DELETE** `/api/sessions/<session_id>`

Delete a session and all associated data.

**Response:**
```json
{
  "message": "Session deleted successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5001/api/sessions/550e8400-e29b-41d4-a716-446655440000
```

---

## Processing Endpoints

### Start Processing

**POST** `/process/<session_id>`

Start the drawing comparison pipeline for a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Processing started"
}
```

**Example:**
```bash
curl -X POST http://localhost:5001/process/550e8400-e29b-41d4-a716-446655440000
```

**Note**: Processing happens asynchronously. Use status endpoint to check progress.

### Get Processing Status

**GET** `/api/process/<session_id>/status`

Get current processing status and progress.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "current_step": 3,
    "total_steps": 5,
    "step_name": "Creating overlays",
    "percentage": 60
  },
  "started_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

**Status Values:**
- `pending`: Not started
- `processing`: In progress
- `completed`: Finished successfully
- `error`: Processing failed

**Example:**
```bash
curl http://localhost:5001/api/process/550e8400-e29b-41d4-a716-446655440000/status
```

### Get Results

**GET** `/results/<session_id>`

Get complete processing results for a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "summary": {
    "overlays_created": 5,
    "analyses_completed": 5,
    "total_time": 45.2
  },
  "changes": [
    {
      "drawing_name": "A-101",
      "critical_change": "Room 101 extended by 10 feet",
      "changes_found": [
        "Room 101 extended from 200 to 300 sq ft",
        "Door relocated from north to west wall"
      ],
      "recommendations": [
        "Update foundation plans",
        "Coordinate with structural engineer"
      ],
      "overlay_url": "/api/files/550e8400.../A-101_overlay.png"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:5001/results/550e8400-e29b-41d4-a716-446655440000
```

### Get Changes Data

**GET** `/api/changes/<session_id>`

Get structured changes data for a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "changes": [
    {
      "drawing_name": "A-101",
      "critical_change": "...",
      "changes_found": [...],
      "analysis_summary": "...",
      "recommendations": [...],
      "overlay_path": "sessions/.../A-101_overlay.png",
      "old_image_path": "sessions/.../A-101_old.png",
      "new_image_path": "sessions/.../A-101_new.png"
    }
  ],
  "total_changes": 5
}
```

**Example:**
```bash
curl http://localhost:5001/api/changes/550e8400-e29b-41d4-a716-446655440000
```

### Get Session Summary

**GET** `/api/session/<session_id>/summary`

Get aggregated summary across all drawings in a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_pages": 5,
  "total_analyses": 5,
  "successful_analyses": 5,
  "failed_analyses": 0,
  "critical_changes": [
    {
      "drawing_name": "A-101",
      "critical_change": "..."
    }
  ],
  "all_changes": [...],
  "all_recommendations": [...],
  "overall_summary": "..."
}
```

**Example:**
```bash
curl http://localhost:5001/api/session/550e8400-e29b-41d4-a716-446655440000/summary
```

---

## Chat Endpoints

### Send Chat Message

**POST** `/api/chat/<session_id>`

Send a message to the AI chatbot.

**Request:**
```json
{
  "message": "What are the typical costs for these changes?"
}
```

**Response:**
```json
{
  "response": "Based on the changes detected in your drawings...",
  "timestamp": "2024-01-15T10:40:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:5001/api/chat/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the typical costs for these changes?"}'
```

### Get Suggested Questions

**GET** `/api/chat/<session_id>/suggested`

Get context-aware suggested questions.

**Response:**
```json
{
  "questions": [
    "What are the typical costs for these changes?",
    "How long should this project take to complete?",
    "What permits might be required for these modifications?",
    "Are there any safety considerations I should be aware of?",
    "What's the best sequence for implementing these changes?"
  ]
}
```

**Example:**
```bash
curl http://localhost:5001/api/chat/550e8400-e29b-41d4-a716-446655440000/suggested
```

### Get Chat History

**GET** `/api/chat/<session_id>/history`

Get conversation history for a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "What are the typical costs?",
      "timestamp": "2024-01-15T10:40:00Z"
    },
    {
      "role": "assistant",
      "content": "Based on the changes...",
      "timestamp": "2024-01-15T10:40:05Z"
    }
  ],
  "total_messages": 2
}
```

**Example:**
```bash
curl http://localhost:5001/api/chat/550e8400-e29b-41d4-a716-446655440000/history
```

---

## File Endpoints

### Get File

**GET** `/api/files/<session_id>/<filename>`

Download a file from a session.

**Query Parameters:**
- `type`: File type (`overlay`, `old`, `new`, `analysis`)

**Response:** File content (binary)

**Example:**
```bash
curl http://localhost:5001/api/files/550e8400-e29b-41d4-a716-446655440000/A-101_overlay.png
```

### Get Signed URL

**GET** `/api/files/<session_id>/<filename>/url`

Get a signed URL for temporary file access (GCS only).

**Query Parameters:**
- `expiration`: Expiration time in minutes (default: 60)

**Response:**
```json
{
  "url": "https://storage.googleapis.com/...",
  "expires_at": "2024-01-15T11:40:00Z"
}
```

**Example:**
```bash
curl http://localhost:5001/api/files/550e8400-e29b-41d4-a716-446655440000/A-101_overlay.png/url?expiration=120
```

### List Session Files

**GET** `/api/files/<session_id>`

List all files in a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "files": [
    {
      "filename": "A-101_overlay.png",
      "type": "overlay",
      "size": 1048576,
      "url": "/api/files/550e8400.../A-101_overlay.png"
    },
    {
      "filename": "A-101_old.png",
      "type": "old",
      "size": 2097152,
      "url": "/api/files/550e8400.../A-101_old.png"
    }
  ],
  "total_files": 15
}
```

**Example:**
```bash
curl http://localhost:5001/api/files/550e8400-e29b-41d4-a716-446655440000
```

---

## WebSocket Events

**Note**: WebSocket support is planned but not yet implemented.

### Planned Events

- `processing_started`: Processing begins
- `processing_progress`: Progress update
- `processing_completed`: Processing finished
- `processing_error`: Processing failed

---

## Rate Limiting

**Current**: No rate limiting (to be implemented)

**Planned Limits:**
- Upload: 10 requests/minute
- Processing: 5 requests/minute
- Chat: 30 requests/minute
- General: 100 requests/minute

## CORS

**Current**: CORS not configured (all origins allowed)

**Production**: Should restrict to specific domains

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:5001"

# Upload files
with open("old.pdf", "rb") as old_file, open("new.pdf", "rb") as new_file:
    files = {
        "old_file": old_file,
        "new_file": new_file
    }
    response = requests.post(f"{BASE_URL}/upload", files=files)
    session_id = response.json()["session_id"]

# Start processing
requests.post(f"{BASE_URL}/process/{session_id}")

# Check status
status = requests.get(f"{BASE_URL}/api/process/{session_id}/status").json()
print(f"Status: {status['status']}")

# Get results
results = requests.get(f"{BASE_URL}/results/{session_id}").json()
print(f"Overlays created: {results['summary']['overlays_created']}")
```

### JavaScript

```javascript
const BASE_URL = "http://localhost:5001";

// Upload files
const formData = new FormData();
formData.append("old_file", oldFile);
formData.append("new_file", newFile);

const uploadResponse = await fetch(`${BASE_URL}/upload`, {
  method: "POST",
  body: formData
});

const { session_id } = await uploadResponse.json();

// Start processing
await fetch(`${BASE_URL}/process/${session_id}`, {
  method: "POST"
});

// Poll for status
const checkStatus = async () => {
  const response = await fetch(`${BASE_URL}/api/process/${session_id}/status`);
  const status = await response.json();
  
  if (status.status === "completed") {
    const results = await fetch(`${BASE_URL}/results/${session_id}`);
    return await results.json();
  } else {
    setTimeout(checkStatus, 2000);
  }
};
```

### cURL

```bash
# Complete workflow
SESSION_ID=$(curl -X POST http://localhost:5001/upload \
  -F "old_file=@old.pdf" \
  -F "new_file=@new.pdf" | jq -r .session_id)

curl -X POST http://localhost:5001/process/$SESSION_ID

# Wait and check results
sleep 30
curl http://localhost:5001/results/$SESSION_ID
```

---

**Next Steps**: See [PIPELINE.md](./PIPELINE.md) for processing pipeline details or [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for API troubleshooting.

