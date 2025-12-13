# Sequence Diagrams

## BuildTrace - Construction Drawing Comparison Platform

**Document Version:** 1.0  
**Date:** December 2025

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Drawing Upload Flow](#2-drawing-upload-flow)
3. [Comparison Job Creation](#3-comparison-job-creation)
4. [Streaming Pipeline Processing](#4-streaming-pipeline-processing)
5. [Results Retrieval](#5-results-retrieval)
6. [Chatbot Interaction](#6-chatbot-interaction)
7. [Summary Regeneration](#7-summary-regeneration)

---

## 1. Authentication Flow

### 1.1 Google OAuth 2.0 Login

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant Google as Google OAuth
    participant DB as Cloud SQL
    
    User->>Browser: Click "Sign in with Google"
    Browser->>Frontend: Handle click event
    Frontend->>Backend: GET /api/v1/auth/google/login
    Backend->>Backend: Generate OAuth state token
    Backend-->>Frontend: {auth_url, state}
    Frontend->>Browser: Redirect to auth_url
    Browser->>Google: OAuth consent screen
    User->>Google: Grant permission
    Google->>Backend: GET /api/v1/auth/google/callback?code=XXX
    Backend->>Google: Exchange code for tokens
    Google-->>Backend: {access_token, id_token}
    Backend->>Google: GET /userinfo (with access_token)
    Google-->>Backend: {email, name, picture}
    Backend->>DB: SELECT user WHERE email = ?
    alt User exists
        DB-->>Backend: User record
        Backend->>DB: UPDATE last_login
    else New user
        Backend->>DB: INSERT INTO users
        DB-->>Backend: New user record
    end
    Backend->>Backend: Generate JWT token
    Backend-->>Browser: Set-Cookie: session + Redirect to frontend
    Browser->>Frontend: Load dashboard with session
    Frontend->>Backend: GET /api/v1/auth/me (with JWT)
    Backend-->>Frontend: {user_id, email, name}
    Frontend->>Browser: Display logged-in state
```

### 1.2 Logout Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    
    User->>Frontend: Click "Logout"
    Frontend->>Backend: POST /api/v1/auth/logout
    Backend->>Backend: Invalidate session
    Backend-->>Frontend: {success: true}
    Frontend->>Frontend: Clear auth store
    Frontend->>Frontend: Clear localStorage
    Frontend-->>User: Redirect to login page
```

---

## 2. Drawing Upload Flow

### 2.1 Single File Upload

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant GCS as Cloud Storage
    participant DB as Cloud SQL
    
    User->>Frontend: Drop/Select PDF file
    Frontend->>Frontend: Validate file type & size
    alt Invalid file
        Frontend-->>User: Show error message
    else Valid file
        Frontend->>Frontend: Show file preview
        Frontend->>Backend: POST /api/v1/drawings/upload<br/>(multipart/form-data)
        Backend->>Backend: Validate file
        Backend->>Backend: Generate drawing_version_id
        Backend->>GCS: Upload file to bucket
        GCS-->>Backend: Upload success
        Backend->>DB: INSERT drawing record
        Backend->>DB: INSERT drawing_version record
        DB-->>Backend: Records created
        Backend-->>Frontend: {drawing_version_id, drawing_name}
        Frontend-->>User: Show upload success
    end
```

### 2.2 Comparison Upload Flow (Both Files)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant GCS as Cloud Storage
    participant DB as Cloud SQL
    
    Note over User,DB: Upload Baseline Drawing
    User->>Frontend: Drop baseline PDF
    Frontend->>Backend: POST /api/v1/drawings/upload
    Backend->>GCS: Upload to GCS
    Backend->>DB: Create DrawingVersion
    Backend-->>Frontend: {drawing_version_id: "old_id"}
    
    Note over User,DB: Upload Revised Drawing with old_version_id
    User->>Frontend: Drop revised PDF
    Frontend->>Backend: POST /api/v1/drawings/upload<br/>{old_version_id: "old_id"}
    Backend->>GCS: Upload to GCS
    Backend->>DB: Create DrawingVersion
    Backend->>Backend: Trigger job creation
    Note right of Backend: See Sequence 3 for job creation
    Backend-->>Frontend: {drawing_version_id: "new_id", job_id: "job_id"}
    Frontend-->>User: Show "Processing..." state
```

---

## 3. Comparison Job Creation

### 3.1 Legacy Batch Mode

```mermaid
sequenceDiagram
    autonumber
    participant Backend as Flask Backend
    participant Orchestrator as OrchestratorService
    participant DB as Cloud SQL
    participant PubSub as Cloud Pub/Sub
    
    Backend->>Orchestrator: create_comparison_job(<br/>old_version_id, new_version_id,<br/>project_id, user_id)
    Orchestrator->>DB: INSERT INTO jobs
    Orchestrator->>DB: INSERT INTO job_stages<br/>(ocr_old, ocr_new, diff, summary)
    DB-->>Orchestrator: Job & stages created
    
    alt Pub/Sub enabled
        Orchestrator->>PubSub: Publish OCR task (old version)
        Orchestrator->>PubSub: Publish OCR task (new version)
        PubSub-->>Orchestrator: Message published
    else Synchronous mode
        Orchestrator->>Orchestrator: Call OCRWorker.process()
    end
    
    Orchestrator->>DB: UPDATE job SET status='in_progress'
    Orchestrator-->>Backend: Return job_id
```

### 3.2 Streaming Mode (Per-Page)

```mermaid
sequenceDiagram
    autonumber
    participant Backend as Flask Backend
    participant Orchestrator as OrchestratorService
    participant Extractor as PageExtractorService
    participant GCS as Cloud Storage
    participant DB as Cloud SQL
    participant PubSub as Cloud Pub/Sub
    
    Backend->>Orchestrator: create_streaming_job(...)
    Orchestrator->>Extractor: extract_pages(old_pdf, job_id, 'old')
    Extractor->>GCS: Download old PDF
    Extractor->>Extractor: Convert PDF to PNG (per page)
    
    loop For each page
        Extractor->>GCS: Upload page_{n}.png
    end
    Extractor-->>Orchestrator: {total_pages, pages: [...]}
    
    Orchestrator->>Extractor: extract_pages(new_pdf, job_id, 'new')
    Extractor->>GCS: Download new PDF
    Extractor->>Extractor: Convert PDF to PNG (per page)
    
    loop For each page
        Extractor->>GCS: Upload page_{n}.png
    end
    Extractor-->>Orchestrator: {total_pages, pages: [...]}
    
    Orchestrator->>DB: INSERT INTO jobs (total_pages = N)
    
    loop For each page (1 to N)
        Orchestrator->>DB: INSERT INTO job_stages<br/>(stage='ocr', page_number=n)
        Orchestrator->>PubSub: Publish OCR task for page n
    end
    
    Orchestrator-->>Backend: Return job_id
```

---

## 4. Streaming Pipeline Processing

### 4.1 Per-Page OCR → Diff → Summary Flow

```mermaid
sequenceDiagram
    autonumber
    participant PubSub as Cloud Pub/Sub
    participant OCR as OCR Worker
    participant Diff as Diff Worker
    participant Summary as Summary Worker
    participant Orchestrator as OrchestratorService
    participant DB as Cloud SQL
    participant GCS as Cloud Storage
    participant AI as Gemini API
    
    Note over PubSub,AI: Page 1 Processing
    
    PubSub->>OCR: Message: {job_id, page_number: 1, old_page_gcs, new_page_gcs}
    OCR->>GCS: Download old_page_1.png
    OCR->>GCS: Download new_page_1.png
    OCR->>AI: Gemini Vision OCR (old page)
    AI-->>OCR: OCR result (old)
    OCR->>AI: Gemini Vision OCR (new page)
    AI-->>OCR: OCR result (new)
    OCR->>GCS: Upload OCR results JSON
    OCR->>DB: UPDATE job_stages SET status='completed'
    OCR->>Orchestrator: on_page_ocr_complete(job_id, page_number=1, ...)
    
    Note over Orchestrator,AI: Immediately trigger diff (no waiting)
    
    Orchestrator->>DB: INSERT job_stages (stage='diff', page_number=1)
    Orchestrator->>PubSub: Publish diff task for page 1
    
    PubSub->>Diff: Message: {job_id, page_number: 1, old_ocr_ref, new_ocr_ref}
    Diff->>GCS: Download page images
    Diff->>Diff: SIFT alignment
    Diff->>Diff: Compute differences
    Diff->>Diff: Generate overlay image
    Diff->>GCS: Upload overlay.png
    Diff->>DB: INSERT diff_results (page_number=1)
    Diff->>DB: UPDATE job_stages SET status='completed'
    Diff->>Orchestrator: on_page_diff_complete(job_id, page_number=1, ...)
    
    Note over Orchestrator,AI: Immediately trigger summary (no waiting)
    
    Orchestrator->>DB: INSERT job_stages (stage='summary', page_number=1)
    Orchestrator->>PubSub: Publish summary task for page 1
    
    PubSub->>Summary: Message: {job_id, page_number: 1, diff_result_id}
    Summary->>GCS: Download overlay JSON
    Summary->>AI: Gemini: Analyze changes
    AI-->>Summary: Summary text + structured data
    Summary->>DB: INSERT change_summaries
    Summary->>DB: UPDATE job_stages SET status='completed'
    Summary->>Orchestrator: on_page_summary_complete(job_id, page_number=1)
    
    Note over Orchestrator,DB: Check if all pages complete
    
    Orchestrator->>DB: SELECT COUNT(*) FROM job_stages<br/>WHERE stage='summary' AND status='completed'
    alt All pages complete
        Orchestrator->>DB: UPDATE jobs SET status='completed'
    else More pages pending
        Note over Orchestrator: Continue processing other pages
    end
```

### 4.2 Parallel Page Processing

```mermaid
sequenceDiagram
    autonumber
    participant PubSub as Cloud Pub/Sub
    participant OCR1 as OCR Worker 1
    participant OCR2 as OCR Worker 2
    participant OCR3 as OCR Worker 3
    participant DB as Cloud SQL
    
    Note over PubSub,DB: Multiple pages processed in parallel
    
    par Page 1
        PubSub->>OCR1: OCR task (page 1)
        OCR1->>OCR1: Process page 1
        OCR1->>DB: Complete page 1
    and Page 2
        PubSub->>OCR2: OCR task (page 2)
        OCR2->>OCR2: Process page 2
        OCR2->>DB: Complete page 2
    and Page 3
        PubSub->>OCR3: OCR task (page 3)
        OCR3->>OCR3: Process page 3
        OCR3->>DB: Complete page 3
    end
    
    Note over DB: Results appear as each page completes
```

---

## 5. Results Retrieval

### 5.1 Job Status Polling

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant DB as Cloud SQL
    
    loop Every 2 seconds until complete
        Frontend->>Backend: GET /api/v1/jobs/{job_id}/progress
        Backend->>DB: SELECT job, job_stages, diff_results
        DB-->>Backend: Job data with per-page status
        Backend-->>Frontend: {status, total_pages, pages: [<br/>  {page_number: 1, ocr_status, diff_status, summary_status},<br/>  ...]}
        
        alt Page completed
            Frontend->>Frontend: Update UI with page results
            Frontend-->>User: Show completed page in sidebar
        end
        
        alt Job completed
            Frontend->>Frontend: Stop polling
            Frontend-->>User: Show "View Results" button
        end
    end
```

### 5.2 Load Full Results

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant DB as Cloud SQL
    participant GCS as Cloud Storage
    
    User->>Frontend: Navigate to /results?jobId=XXX
    Frontend->>Backend: GET /api/v1/jobs/{job_id}/results
    Backend->>DB: SELECT job, diff_results, change_summaries
    DB-->>Backend: Full job data
    Backend-->>Frontend: {job_id, status, diffs: [...], summary: {...}}
    
    Frontend->>Backend: GET /api/v1/overlays/{diff_id}/images
    Backend->>GCS: Generate signed URLs
    GCS-->>Backend: Signed URLs for images
    Backend-->>Frontend: {overlay_url, baseline_url, revised_url}
    
    Frontend->>GCS: Fetch overlay image (via signed URL)
    GCS-->>Frontend: Image data
    Frontend-->>User: Display overlay in viewer
```

---

## 6. Chatbot Interaction

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant Chatbot as ChatbotService
    participant DB as Cloud SQL
    participant AI as Gemini API
    participant Web as DuckDuckGo API
    
    User->>Frontend: Type question + press Enter
    Frontend->>Backend: POST /api/v1/chat/message<br/>{session_id, message, job_id}
    Backend->>Chatbot: send_message(session_id, message)
    
    Chatbot->>DB: Fetch session context<br/>(job results, summaries)
    DB-->>Chatbot: Context data
    
    alt Question needs web search
        Chatbot->>Web: Search for current info
        Web-->>Chatbot: Search results
    end
    
    Chatbot->>Chatbot: Build prompt with context
    Chatbot->>AI: Generate response
    AI-->>Chatbot: Response text
    
    Chatbot->>DB: Save conversation message
    Chatbot-->>Backend: {response, suggested_questions}
    Backend-->>Frontend: {message, response, suggestions}
    Frontend-->>User: Display AI response
```

---

## 7. Summary Regeneration

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as Flask Backend
    participant Orchestrator as OrchestratorService
    participant PubSub as Cloud Pub/Sub
    participant Summary as Summary Worker
    participant AI as Gemini API
    participant DB as Cloud SQL
    
    User->>Frontend: Click "Regenerate" button
    Frontend->>Backend: POST /api/v1/summaries/{diff_id}/regenerate
    Backend->>Orchestrator: trigger_summary_regeneration(diff_id)
    
    Orchestrator->>DB: Create new JobStage (summary)
    Orchestrator->>PubSub: Publish summary task
    PubSub-->>Orchestrator: Published
    
    Orchestrator-->>Backend: {stage_id}
    Backend-->>Frontend: {status: 'regenerating'}
    Frontend-->>User: Show loading state
    
    PubSub->>Summary: Summary task
    Summary->>AI: Analyze with fresh prompt
    AI-->>Summary: New summary
    Summary->>DB: INSERT new change_summary<br/>SET is_active = true
    Summary->>DB: UPDATE old summaries<br/>SET is_active = false
    
    Frontend->>Backend: GET /api/v1/summaries/{diff_id}
    Backend->>DB: SELECT active summary
    DB-->>Backend: New summary
    Backend-->>Frontend: {summary_text, ...}
    Frontend-->>User: Display new summary
```

---

## Summary

This document covered the main sequence diagrams for BuildTrace:

| Flow | Description | Key Components |
|------|-------------|----------------|
| **Authentication** | Google OAuth login/logout | Frontend, Backend, Google OAuth |
| **Drawing Upload** | File upload with validation | Frontend, Backend, GCS |
| **Job Creation** | Legacy batch and streaming modes | Orchestrator, DB, Pub/Sub |
| **Streaming Pipeline** | Per-page OCR → Diff → Summary | Workers, Orchestrator |
| **Results Retrieval** | Polling and full results load | Frontend, Backend, GCS |
| **Chatbot** | AI-powered Q&A | Chatbot Service, Gemini |
| **Regeneration** | Summary regeneration | Orchestrator, Workers |

---

*End of Sequence Diagrams Document*

