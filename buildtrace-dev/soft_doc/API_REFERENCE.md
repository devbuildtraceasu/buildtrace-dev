# API Reference

## BuildTrace - Construction Drawing Comparison Platform

**Document Version:** 1.0  
**Date:** December 2025  
**Base URL:** `https://buildtrace-backend-136394139608.us-west2.run.app`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Projects API](#3-projects-api)
4. [Drawings API](#4-drawings-api)
5. [Jobs API](#5-jobs-api)
6. [Overlays API](#6-overlays-api)
7. [Summaries API](#7-summaries-api)
8. [Chat API](#8-chat-api)
9. [Error Responses](#9-error-responses)

---

## 1. Overview

### 1.1 Base URLs

| Environment | URL |
|-------------|-----|
| **Production** | `https://buildtrace-backend-136394139608.us-west2.run.app` |
| **Development** | `http://localhost:5001` |

### 1.2 Request Headers

```http
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

### 1.3 Response Format

All responses follow this structure:

```json
{
  "data": { ... },
  "error": null,
  "message": "Success"
}
```

Error responses:

```json
{
  "data": null,
  "error": "Error code",
  "message": "Human-readable error message"
}
```

---

## 2. Authentication

### 2.1 Google OAuth Login

Initiates Google OAuth 2.0 flow.

```http
GET /api/v1/auth/google/login
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_token"
}
```

### 2.2 OAuth Callback

Handles Google OAuth callback (internal use).

```http
GET /api/v1/auth/google/callback?code=xxx&state=xxx
```

**Response:** Redirects to frontend with session cookie set.

### 2.3 Get Current User

Get the authenticated user's profile.

```http
GET /api/v1/auth/me
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "company": "ACME Corp",
  "role": "architect",
  "organization_id": "uuid",
  "email_verified": true,
  "is_active": true
}
```

### 2.4 Logout

End the current session.

```http
POST /api/v1/auth/logout
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 3. Projects API

### 3.1 List Projects

Get all projects for the authenticated user.

```http
GET /api/v1/projects
GET /api/v1/projects?user_id=xxx&include_counts=true
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | string | Filter by user (optional) |
| include_counts | boolean | Include document/drawing/comparison counts |

**Response:**
```json
{
  "projects": [
    {
      "project_id": "uuid",
      "name": "Mirage Tower Phase 2",
      "description": "Commercial building project",
      "status": "active",
      "created_at": "2025-11-20T10:00:00Z",
      "updated_at": "2025-11-28T15:30:00Z",
      "document_count": 12,
      "drawing_count": 45,
      "comparison_count": 8
    }
  ]
}
```

### 3.2 Create Project

Create a new project.

```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "New Project",
  "description": "Project description",
  "project_number": "PRJ-001",
  "user_id": "uuid"
}
```

**Response:**
```json
{
  "project": {
    "project_id": "uuid",
    "name": "New Project",
    "description": "Project description",
    "status": "active",
    "created_at": "2025-12-01T10:00:00Z"
  }
}
```

### 3.3 Get Project Details

Get a specific project by ID.

```http
GET /api/v1/projects/{project_id}
```

**Response:**
```json
{
  "project": {
    "project_id": "uuid",
    "name": "Mirage Tower Phase 2",
    "description": "...",
    "project_number": "MT-2025",
    "client_name": "Mirage Corp",
    "location": "Dubai, UAE",
    "status": "active",
    "created_at": "2025-11-20T10:00:00Z"
  }
}
```

### 3.4 List Project Documents

Get all documents in a project.

```http
GET /api/v1/projects/{project_id}/documents
```

**Response:**
```json
{
  "documents": [
    {
      "document_id": "uuid",
      "name": "A-101_Rev2.pdf",
      "file_type": "application/pdf",
      "file_size": 2456789,
      "uploaded_at": "2025-11-28T10:00:00Z",
      "page_count": 3,
      "status": "ready"
    }
  ]
}
```

### 3.5 List Project Drawings

Get all drawings in a project.

```http
GET /api/v1/projects/{project_id}/drawings
```

**Response:**
```json
{
  "drawings": [
    {
      "drawing_id": "uuid",
      "drawing_name": "A-101",
      "version_count": 3,
      "latest_version": "Rev C",
      "last_updated": "2025-11-28T10:00:00Z"
    }
  ]
}
```

### 3.6 List Project Comparisons

Get all comparison jobs in a project.

```http
GET /api/v1/projects/{project_id}/comparisons
```

**Response:**
```json
{
  "comparisons": [
    {
      "job_id": "uuid",
      "old_drawing": "A-101 Rev A",
      "new_drawing": "A-101 Rev B",
      "status": "completed",
      "change_count": 15,
      "created_at": "2025-11-28T10:00:00Z"
    }
  ]
}
```

---

## 4. Drawings API

### 4.1 Upload Drawing

Upload a drawing file and optionally start a comparison job.

```http
POST /api/v1/drawings/upload
Content-Type: multipart/form-data

file: <binary>
project_id: "uuid"
user_id: "uuid" (optional)
old_version_id: "uuid" (optional - triggers job creation)
```

**Response (without old_version_id):**
```json
{
  "drawing_version_id": "uuid",
  "drawing_name": "A-101",
  "version_number": 1,
  "status": "uploaded"
}
```

**Response (with old_version_id):**
```json
{
  "drawing_version_id": "uuid",
  "drawing_name": "A-101",
  "version_number": 2,
  "job_id": "uuid",
  "status": "uploaded"
}
```

### 4.2 Get Drawing

Get drawing version details.

```http
GET /api/v1/drawings/{drawing_version_id}
```

**Response:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "drawing_name": "A-101",
  "version_number": 2,
  "version_label": "Rev B",
  "upload_date": "2025-11-28T10:00:00Z",
  "ocr_status": "completed",
  "file_size": 2456789
}
```

### 4.3 List Drawing Versions

Get all versions of a drawing.

```http
GET /api/v1/drawings/{drawing_version_id}/versions
```

**Response:**
```json
{
  "drawing_name": "A-101",
  "versions": [
    {
      "id": "uuid",
      "version_number": 1,
      "version_label": "Rev A",
      "upload_date": "2025-11-20T10:00:00Z"
    },
    {
      "id": "uuid",
      "version_number": 2,
      "version_label": "Rev B",
      "upload_date": "2025-11-28T10:00:00Z"
    }
  ]
}
```

---

## 5. Jobs API

### 5.1 Create Job

Create a new comparison job.

```http
POST /api/v1/jobs
Content-Type: application/json

{
  "old_drawing_version_id": "uuid",
  "new_drawing_version_id": "uuid",
  "project_id": "uuid",
  "user_id": "uuid"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "created"
}
```

### 5.2 Get Job Status

Get the current status of a job.

```http
GET /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "old_drawing_version_id": "uuid",
  "new_drawing_version_id": "uuid",
  "status": "in_progress",
  "total_pages": 3,
  "created_at": "2025-11-28T10:00:00Z",
  "started_at": "2025-11-28T10:00:05Z",
  "completed_at": null,
  "error_message": null
}
```

### 5.3 Get Job Stages

Get detailed stage status for a job.

```http
GET /api/v1/jobs/{job_id}/stages
```

**Response:**
```json
{
  "job_id": "uuid",
  "stages": [
    {
      "id": "uuid",
      "stage": "ocr",
      "page_number": 1,
      "status": "completed",
      "started_at": "2025-11-28T10:00:10Z",
      "completed_at": "2025-11-28T10:01:30Z"
    },
    {
      "id": "uuid",
      "stage": "diff",
      "page_number": 1,
      "status": "in_progress",
      "started_at": "2025-11-28T10:01:35Z",
      "completed_at": null
    },
    {
      "id": "uuid",
      "stage": "summary",
      "page_number": 1,
      "status": "pending",
      "started_at": null,
      "completed_at": null
    }
  ]
}
```

### 5.4 Get Job Progress (Streaming)

Get per-page, per-stage progress for streaming UI updates.

```http
GET /api/v1/jobs/{job_id}/progress
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "in_progress",
  "total_pages": 3,
  "progress": {
    "ocr": { "completed": 2, "total": 3 },
    "diff": { "completed": 1, "total": 3 },
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
        "diff_result_id": "uuid",
        "overlay_url": "https://...",
        "changes_detected": true,
        "change_count": 5
      },
      "summary": {
        "summary_id": "uuid",
        "summary_text": "5 changes detected..."
      }
    },
    {
      "page_number": 2,
      "drawing_name": "A-102",
      "ocr_status": "completed",
      "diff_status": "in_progress",
      "summary_status": "pending"
    }
  ]
}
```

### 5.5 Get Job Results

Get complete results for a finished job.

```http
GET /api/v1/jobs/{job_id}/results
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "completed_at": "2025-11-28T10:05:00Z",
  "diffs": [
    {
      "diff_result_id": "uuid",
      "page_number": 1,
      "drawing_name": "A-101",
      "overlay_ref": "gs://bucket/overlays/...",
      "alignment_score": 0.98,
      "changes_detected": true,
      "change_count": 5,
      "summary": {
        "id": "uuid",
        "summary_text": "5 changes detected...",
        "categories": {
          "Architectural": 3,
          "MEP": 2
        }
      }
    }
  ]
}
```

### 5.6 List Jobs

Get jobs for the authenticated user.

```http
GET /api/v1/jobs
GET /api/v1/jobs?user_id=xxx&status=completed&limit=20
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | string | Filter by user |
| status | string | Filter by status |
| limit | integer | Max results (default 50) |

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "project_name": "Mirage Tower",
      "old_drawing": "A-101 Rev A",
      "new_drawing": "A-101 Rev B",
      "status": "completed",
      "change_count": 15,
      "created_at": "2025-11-28T10:00:00Z"
    }
  ]
}
```

### 5.7 Get OCR Log

Get OCR processing logs for debugging.

```http
GET /api/v1/jobs/{job_id}/ocr-log
```

**Response:**
```json
{
  "job_id": "uuid",
  "ocr_logs": [
    {
      "drawing_version_id": "uuid",
      "drawing_name": "A-101",
      "log": {
        "pages": [
          {
            "page_number": 1,
            "drawing_name": "A-101",
            "extracted_info": {
              "title_block": {...},
              "text_blocks": [...]
            },
            "processed_at": "2025-11-28T10:01:00Z"
          }
        ]
      }
    }
  ]
}
```

---

## 6. Overlays API

### 6.1 Get Overlay

Get overlay data for a diff result.

```http
GET /api/v1/overlays/{diff_result_id}
```

**Response:**
```json
{
  "active_overlay": {
    "overlay_id": "uuid",
    "diff_result_id": "uuid",
    "overlay_ref": "gs://bucket/...",
    "is_active": true,
    "created_at": "2025-11-28T10:02:00Z"
  },
  "overlays": []
}
```

### 6.2 Get Overlay Image URL

Get signed URL for overlay image.

```http
GET /api/v1/overlays/{diff_result_id}/image-url
```

**Response:**
```json
{
  "diff_result_id": "uuid",
  "overlay_image_url": "https://storage.googleapis.com/...",
  "page_number": 1,
  "drawing_name": "A-101"
}
```

### 6.3 Get All Image URLs

Get signed URLs for all images (overlay, baseline, revised).

```http
GET /api/v1/overlays/{diff_result_id}/images
```

**Response:**
```json
{
  "diff_result_id": "uuid",
  "overlay_image_url": "https://...",
  "baseline_image_url": "https://...",
  "revised_image_url": "https://...",
  "page_number": 1,
  "drawing_name": "A-101"
}
```

### 6.4 Create Manual Overlay

Create a human-edited overlay.

```http
POST /api/v1/overlays/{diff_result_id}/manual
Content-Type: application/json

{
  "overlay_data": {...},
  "user_id": "uuid",
  "metadata": {...},
  "auto_regenerate": true
}
```

**Response:**
```json
{
  "success": true,
  "overlay_id": "uuid"
}
```

---

## 7. Summaries API

### 7.1 Get Summaries

Get summaries for a diff result.

```http
GET /api/v1/summaries/{diff_result_id}
```

**Response:**
```json
{
  "active_summary": {
    "id": "uuid",
    "summary_text": "15 changes detected...",
    "summary_json": {
      "critical_change": "None",
      "changes": [...],
      "recommendations": [...]
    },
    "source": "machine",
    "ai_model_used": "models/gemini-2.5-pro",
    "created_at": "2025-11-28T10:03:00Z"
  },
  "summaries": []
}
```

### 7.2 Regenerate Summary

Trigger AI summary regeneration.

```http
POST /api/v1/summaries/{diff_result_id}/regenerate
Content-Type: application/json

{
  "overlay_id": "uuid" (optional)
}
```

**Response:**
```json
{
  "success": true,
  "summary_id": "uuid",
  "status": "regenerating"
}
```

### 7.3 Update Summary

Save human-edited summary.

```http
PUT /api/v1/summaries/{summary_id}
Content-Type: application/json

{
  "summary_text": "Updated summary text...",
  "metadata": {...}
}
```

**Response:**
```json
{
  "success": true,
  "summary_id": "uuid",
  "source": "human_corrected"
}
```

---

## 8. Chat API

### 8.1 Send Message

Send a message to the AI chatbot.

```http
POST /api/v1/chat/message
Content-Type: application/json

{
  "session_id": "uuid",
  "message": "Which walls were added?",
  "job_id": "uuid"
}
```

**Response:**
```json
{
  "message": "Which walls were added?",
  "response": "Based on the comparison results, 3 walls were added...",
  "suggested_questions": [
    "What are the dimensions of the new walls?",
    "Are there any structural implications?"
  ],
  "timestamp": "2025-11-28T10:05:00Z"
}
```

### 8.2 Get Suggested Questions

Get AI-suggested questions for a session.

```http
GET /api/v1/chat/suggestions?session_id=xxx&job_id=xxx
```

**Response:**
```json
{
  "suggestions": [
    "What changes were made to the floor plan?",
    "Are there any MEP modifications?",
    "Summarize the structural changes"
  ]
}
```

---

## 9. Error Responses

### 9.1 HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Duplicate resource |
| 413 | Payload Too Large - File exceeds 70 MB |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### 9.2 Error Response Format

```json
{
  "error": "VALIDATION_ERROR",
  "message": "File type not supported. Allowed: PDF, DWG, DXF, PNG, JPG",
  "details": {
    "field": "file",
    "received": "application/zip"
  }
}
```

### 9.3 Common Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `AUTH_REQUIRED` | Authentication required |
| `ACCESS_DENIED` | User doesn't have permission |
| `NOT_FOUND` | Resource not found |
| `FILE_TOO_LARGE` | File exceeds size limit |
| `INVALID_FILE_TYPE` | File type not supported |
| `JOB_IN_PROGRESS` | Job is still processing |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

---

## Health Check

### GET /health

Check API health status.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "enabled",
  "gcs": "enabled",
  "pubsub": "enabled",
  "oauth": "enabled"
}
```

---

*End of API Reference Document*

