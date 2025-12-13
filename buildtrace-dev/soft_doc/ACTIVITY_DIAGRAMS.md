# Activity Diagrams

## BuildTrace - Construction Drawing Comparison Platform

**Document Version:** 1.0  
**Date:** December 2025

---

## Table of Contents

1. [User Authentication Activity](#1-user-authentication-activity)
2. [Drawing Upload Activity](#2-drawing-upload-activity)
3. [Comparison Processing Activity](#3-comparison-processing-activity)
4. [OCR Processing Activity](#4-ocr-processing-activity)
5. [Diff Generation Activity](#5-diff-generation-activity)
6. [Summary Generation Activity](#6-summary-generation-activity)
7. [Results Viewing Activity](#7-results-viewing-activity)
8. [Error Handling Activity](#8-error-handling-activity)

---

## 1. User Authentication Activity

### 1.1 Login Activity

```mermaid
flowchart TD
    A((Start)) --> B{User Authenticated?}
    B -->|Yes| C[Show Dashboard]
    B -->|No| D[Show Login Page]
    D --> E[Click Sign in with Google]
    E --> F[Redirect to Google OAuth]
    F --> G{User Grants Permission?}
    G -->|No| H[Show Error: Access Denied]
    H --> D
    G -->|Yes| I[Receive OAuth Token]
    I --> J{User Exists in DB?}
    J -->|Yes| K[Update Last Login]
    J -->|No| L[Create New User Record]
    K --> M[Generate JWT Token]
    L --> M
    M --> N[Set Session Cookie]
    N --> O[Redirect to Dashboard]
    O --> C
    C --> P((End))
```

### 1.2 Logout Activity

```mermaid
flowchart TD
    A((Start)) --> B[User Clicks Logout]
    B --> C[Send Logout Request to Backend]
    C --> D[Backend Invalidates Session]
    D --> E[Clear JWT Token]
    E --> F[Clear Local Storage]
    F --> G[Clear Auth Store]
    G --> H[Redirect to Login Page]
    H --> I((End))
```

---

## 2. Drawing Upload Activity

### 2.1 Single File Upload

```mermaid
flowchart TD
    A((Start)) --> B[User Selects/Drops File]
    B --> C{Valid File Type?}
    C -->|No| D[Show Error: Invalid Type]
    D --> A
    C -->|Yes| E{File Size ≤ 70MB?}
    E -->|No| F[Show Error: File Too Large]
    F --> A
    E -->|Yes| G[Show Upload Progress]
    G --> H[Send File to Backend]
    H --> I[Backend Validates File]
    I --> J[Generate Unique ID]
    J --> K[Upload to Cloud Storage]
    K --> L{Upload Success?}
    L -->|No| M[Show Error: Upload Failed]
    M --> A
    L -->|Yes| N[Create Database Records]
    N --> O[Return Drawing Version ID]
    O --> P[Show Success State]
    P --> Q((End))
```

### 2.2 Comparison Upload (Both Files)

```mermaid
flowchart TD
    A((Start)) --> B[User Selects Project]
    B --> C{Project Selected?}
    C -->|No| D[Use Default Project]
    C -->|Yes| E[Use Selected Project]
    D --> F
    E --> F[Upload Baseline Drawing]
    F --> G{Baseline Upload Success?}
    G -->|No| H[Show Error]
    H --> A
    G -->|Yes| I[Store old_version_id]
    I --> J[Enable Revised Upload Area]
    J --> K[User Uploads Revised Drawing]
    K --> L{Revised Upload Success?}
    L -->|No| M[Show Error]
    M --> J
    L -->|Yes| N[Both Files Uploaded]
    N --> O[Enable Compare Button]
    O --> P{User Clicks Compare?}
    P -->|No| Q[Wait for User Action]
    Q --> P
    P -->|Yes| R[Trigger Job Creation]
    R --> S[Redirect to Processing Monitor]
    S --> T((End))
```

---

## 3. Comparison Processing Activity

### 3.1 Job Orchestration (High-Level)

```mermaid
flowchart TD
    A((Start)) --> B[Receive Comparison Request]
    B --> C[Create Job Record]
    C --> D{Streaming Mode?}
    D -->|Yes| E[Extract Pages from PDFs]
    D -->|No| F[Legacy Batch Mode]
    E --> G[Create Per-Page Job Stages]
    F --> H[Create Batch Job Stages]
    G --> I[Publish OCR Tasks]
    H --> I
    I --> J[Update Job Status: In Progress]
    J --> K[Return Job ID to Frontend]
    K --> L[Frontend Starts Polling]
    L --> M{All Stages Complete?}
    M -->|No| N[Wait for Worker Callbacks]
    N --> M
    M -->|Yes| O[Update Job Status: Completed]
    O --> P((End))
```

### 3.2 Streaming Pipeline Flow

```mermaid
flowchart TD
    A((Start)) --> B[Extract Pages from Old PDF]
    B --> C[Extract Pages from New PDF]
    C --> D[Determine Total Page Count]
    D --> E[Create Job with total_pages]
    
    E --> F[For Each Page 1 to N]
    F --> G[Publish OCR Task for Page]
    G --> H{More Pages?}
    H -->|Yes| F
    H -->|No| I[All OCR Tasks Published]
    
    I --> J[Workers Process Pages in Parallel]
    
    subgraph Worker Processing
        K[Page OCR Complete] --> L[Trigger Diff for Page]
        L --> M[Page Diff Complete]
        M --> N[Trigger Summary for Page]
        N --> O[Page Summary Complete]
    end
    
    J --> K
    O --> P{All Pages Complete?}
    P -->|No| Q[More Pages Processing...]
    Q --> K
    P -->|Yes| R[Mark Job Complete]
    R --> S((End))
```

---

## 4. OCR Processing Activity

```mermaid
flowchart TD
    A((Start)) --> B[Receive OCR Task from Pub/Sub]
    B --> C[Extract job_id, page_number]
    C --> D[Download Old Page Image from GCS]
    D --> E{Download Success?}
    E -->|No| F[Retry or Mark Failed]
    F --> G{Max Retries?}
    G -->|No| D
    G -->|Yes| H[Mark Stage Failed]
    H --> Z((End))
    
    E -->|Yes| I[Download New Page Image from GCS]
    I --> J{Download Success?}
    J -->|No| F
    J -->|Yes| K[Send Old Image to Gemini Vision]
    K --> L[Extract Text + Bounding Boxes]
    L --> M[Send New Image to Gemini Vision]
    M --> N[Extract Text + Bounding Boxes]
    N --> O[Combine OCR Results]
    O --> P[Save OCR JSON to GCS]
    P --> Q[Update JobStage Status]
    Q --> R[Notify Orchestrator: OCR Complete]
    R --> S[Orchestrator Triggers Diff]
    S --> T((End))
```

### OCR AI Processing Detail

```mermaid
flowchart TD
    A[Image Input] --> B[Resize if Needed]
    B --> C[Convert to Base64]
    C --> D[Build Gemini Prompt]
    D --> E[Call Gemini Vision API]
    E --> F{API Success?}
    F -->|No| G[Retry with Backoff]
    G --> H{Max Retries?}
    H -->|No| E
    H -->|Yes| I[Return Empty Result]
    F -->|Yes| J[Parse Response]
    J --> K[Extract Text Blocks]
    K --> L[Extract Bounding Boxes]
    L --> M[Extract Drawing Metadata]
    M --> N[Build OCR Result JSON]
    N --> O[Return OCR Result]
```

---

## 5. Diff Generation Activity

```mermaid
flowchart TD
    A((Start)) --> B[Receive Diff Task]
    B --> C[Download Old Page Image]
    C --> D[Download New Page Image]
    D --> E[Download OCR Results]
    E --> F[SIFT Feature Detection]
    F --> G[Find Matching Keypoints]
    G --> H[Calculate Affine Transform]
    H --> I{Alignment Score ≥ Threshold?}
    I -->|No| J[Log Warning: Poor Alignment]
    I -->|Yes| K[Continue]
    J --> K
    K --> L[Align New Image to Old]
    L --> M[Pixel-wise Comparison]
    M --> N[Identify Changed Regions]
    N --> O[Classify Changes]
    
    subgraph Classification
        P[Additions - Green]
        Q[Deletions - Red]
        R[Modifications - Yellow]
    end
    
    O --> P
    O --> Q
    O --> R
    
    P --> S[Generate Overlay Image]
    Q --> S
    R --> S
    
    S --> T[Calculate Change Statistics]
    T --> U[Save Overlay to GCS]
    U --> V[Create DiffResult Record]
    V --> W[Update JobStage Status]
    W --> X[Notify Orchestrator: Diff Complete]
    X --> Y[Orchestrator Triggers Summary]
    Y --> Z((End))
```

---

## 6. Summary Generation Activity

```mermaid
flowchart TD
    A((Start)) --> B[Receive Summary Task]
    B --> C[Fetch DiffResult from DB]
    C --> D[Download Overlay JSON from GCS]
    D --> E[Build AI Prompt]
    
    subgraph Prompt Construction
        F[System Prompt: Construction Expert]
        G[Include Change Data]
        H[Include Drawing Name/Page]
        I[Request Structured Output]
    end
    
    E --> F
    F --> G
    G --> H
    H --> I
    
    I --> J[Call Gemini 2.5 Pro API]
    J --> K{API Success?}
    K -->|No| L[Retry with Backoff]
    L --> M{Max Retries?}
    M -->|No| J
    M -->|Yes| N[Use Fallback Summary]
    K -->|Yes| O[Parse AI Response]
    N --> P
    O --> P[Extract Summary Text]
    P --> Q[Extract Change List]
    Q --> R[Extract Categories]
    R --> S[Extract Recommendations]
    S --> T[Create ChangeSummary Record]
    T --> U[Update JobStage Status]
    U --> V[Notify Orchestrator: Summary Complete]
    V --> W{All Pages Done?}
    W -->|No| X[Continue Other Pages]
    W -->|Yes| Y[Mark Job Complete]
    Y --> Z((End))
```

---

## 7. Results Viewing Activity

### 7.1 Load Results Page

```mermaid
flowchart TD
    A((Start)) --> B[Navigate to /results?jobId=X]
    B --> C{User Authenticated?}
    C -->|No| D[Redirect to Login]
    D --> E((End))
    C -->|Yes| F[Fetch Job Data]
    F --> G{Job Exists?}
    G -->|No| H[Show 404 Error]
    H --> E
    G -->|Yes| I{Job Completed?}
    I -->|No| J[Show Processing Monitor]
    J --> K[Poll for Updates]
    K --> I
    I -->|Yes| L[Load Diff Results]
    L --> M[Load Change Summaries]
    M --> N[Load Image URLs]
    N --> O[Render Results Page]
    O --> P[Display KPIs]
    P --> Q[Display Drawing Selector]
    Q --> R[Display Image Viewer]
    R --> S[Display Summary Panel]
    S --> T((End))
```

### 7.2 Image Viewer Interaction

```mermaid
flowchart TD
    A((Start)) --> B[User Selects View Mode]
    B --> C{Which Mode?}
    
    C -->|Overlay| D[Show Overlay Image]
    C -->|Side-by-Side| E[Show Both Images]
    C -->|Baseline Only| F[Show Old Image]
    C -->|Revised Only| G[Show New Image]
    
    D --> H[Apply Current Zoom]
    E --> H
    F --> H
    G --> H
    
    H --> I{User Action?}
    I -->|Zoom In| J[Increase Zoom Level]
    I -->|Zoom Out| K[Decrease Zoom Level]
    I -->|Pan| L[Update Image Position]
    I -->|Reset| M[Reset to Default]
    I -->|Fit| N[Fit to Container]
    I -->|Download| O[Download Current View]
    I -->|Select Drawing| P[Load Different Page]
    I -->|None| Q[Wait]
    
    J --> H
    K --> H
    L --> H
    M --> H
    N --> H
    O --> H
    P --> R[Fetch New Page Data]
    R --> H
    Q --> I
```

---

## 8. Error Handling Activity

### 8.1 Worker Error Handling

```mermaid
flowchart TD
    A((Start)) --> B[Worker Receives Task]
    B --> C[Process Task]
    C --> D{Processing Error?}
    D -->|No| E[Mark Stage Completed]
    E --> F[Continue Pipeline]
    F --> G((End))
    
    D -->|Yes| H[Log Error Details]
    H --> I{Retryable Error?}
    I -->|Yes| J{Retry Count < 5?}
    J -->|Yes| K[Increment Retry Count]
    K --> L[Re-queue Task]
    L --> B
    J -->|No| M[Send to Dead Letter Queue]
    
    I -->|No| M
    M --> N[Mark Stage Failed]
    N --> O[Update Job Status]
    O --> P{Partial Results Available?}
    P -->|Yes| Q[Mark Job Partially Complete]
    P -->|No| R[Mark Job Failed]
    Q --> S[Notify User]
    R --> S
    S --> G
```

### 8.2 API Error Handling

```mermaid
flowchart TD
    A((Start)) --> B[API Request Received]
    B --> C{Authentication Valid?}
    C -->|No| D[Return 401 Unauthorized]
    D --> E((End))
    
    C -->|Yes| F{Authorization Check}
    F -->|No| G[Return 403 Forbidden]
    G --> E
    
    F -->|Yes| H[Validate Input]
    H --> I{Input Valid?}
    I -->|No| J[Return 400 Bad Request]
    J --> E
    
    I -->|Yes| K[Process Request]
    K --> L{Processing Error?}
    L -->|No| M[Return 200 Success]
    M --> E
    
    L -->|Yes| N{Error Type?}
    N -->|Not Found| O[Return 404]
    N -->|Conflict| P[Return 409]
    N -->|Server Error| Q[Return 500]
    N -->|Service Unavailable| R[Return 503]
    
    O --> E
    P --> E
    Q --> S[Log Error Stack Trace]
    S --> E
    R --> E
```

---

## Activity Diagram Summary

| Activity | Description | Key Decision Points |
|----------|-------------|---------------------|
| **Authentication** | OAuth login flow | User exists?, Permission granted? |
| **Upload** | File upload with validation | Valid type?, Size limit?, Upload success? |
| **Job Orchestration** | High-level comparison flow | Streaming mode?, All stages complete? |
| **Streaming Pipeline** | Per-page processing | All pages complete? |
| **OCR Processing** | AI text extraction | Download success?, API success? |
| **Diff Generation** | Change detection | Alignment score threshold? |
| **Summary Generation** | AI summarization | API success?, All pages done? |
| **Results Viewing** | User interaction with results | View mode?, User action? |
| **Error Handling** | Retry and DLQ logic | Retryable?, Max retries? |

---

*End of Activity Diagrams Document*

