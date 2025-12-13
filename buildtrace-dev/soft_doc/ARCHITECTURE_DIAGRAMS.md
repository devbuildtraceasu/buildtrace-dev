# Architecture Diagrams

## BuildTrace - Construction Drawing Comparison Platform

**Document Version:** 1.0  
**Date:** December 2025

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Deployment Architecture](#2-deployment-architecture)
3. [Component Architecture](#3-component-architecture)
4. [Backend Architecture](#4-backend-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Database Architecture](#6-database-architecture)
7. [Message Queue Architecture](#7-message-queue-architecture)
8. [Security Architecture](#8-security-architecture)

---

## 1. System Architecture Overview

### 1.1 High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[🌐 Web Browser]
    end

    subgraph "Edge Layer"
        CDN[☁️ Cloud CDN]
        LB[⚖️ Load Balancer]
    end

    subgraph "Application Layer"
        Frontend[📱 Next.js Frontend<br/>Cloud Run]
        Backend[🔧 Flask Backend<br/>Cloud Run]
    end

    subgraph "Worker Layer"
        OCRWorker[🔍 OCR Worker]
        DiffWorker[⚖️ Diff Worker]
        SummaryWorker[📝 Summary Worker]
    end

    subgraph "Service Layer"
        PubSub[📨 Pub/Sub]
        Secrets[🔐 Secret Manager]
        Logging[📊 Cloud Logging]
    end

    subgraph "Data Layer"
        CloudSQL[(🗄️ Cloud SQL<br/>PostgreSQL)]
        GCS[(📦 Cloud Storage<br/>GCS)]
    end

    subgraph "AI Layer"
        Gemini[🤖 Google Gemini]
        OpenAI[🧠 OpenAI GPT]
    end

    Browser --> CDN
    CDN --> LB
    LB --> Frontend
    Frontend --> Backend
    Backend --> CloudSQL
    Backend --> GCS
    Backend --> PubSub
    Backend --> Secrets

    PubSub --> OCRWorker
    PubSub --> DiffWorker
    PubSub --> SummaryWorker

    OCRWorker --> Gemini
    OCRWorker --> GCS
    OCRWorker --> CloudSQL

    DiffWorker --> GCS
    DiffWorker --> CloudSQL

    SummaryWorker --> Gemini
    SummaryWorker --> OpenAI
    SummaryWorker --> CloudSQL

    Backend --> Logging
    OCRWorker --> Logging
    DiffWorker --> Logging
    SummaryWorker --> Logging
```

### 1.2 System Components

| Layer | Component | Technology | Purpose |
|-------|-----------|------------|---------|
| **Client** | Web Browser | Chrome, Firefox, Safari | User interface access |
| **Edge** | Load Balancer | Cloud Run Ingress | Traffic distribution |
| **Application** | Frontend | Next.js 14 on Cloud Run | User interface |
| **Application** | Backend | Flask on Cloud Run | REST API |
| **Worker** | OCR Worker | Python on Cloud Run Jobs | Text extraction |
| **Worker** | Diff Worker | Python on Cloud Run Jobs | Change detection |
| **Worker** | Summary Worker | Python on Cloud Run Jobs | AI summarization |
| **Data** | Database | Cloud SQL PostgreSQL 17 | Structured data |
| **Data** | File Storage | Cloud Storage | Binary files |
| **Service** | Message Queue | Cloud Pub/Sub | Async processing |
| **AI** | Vision AI | Google Gemini 2.5 Pro | OCR and analysis |

---

## 2. Deployment Architecture

### 2.1 Google Cloud Platform Layout

```mermaid
graph TB
    subgraph "GCP Project: buildtrace-dev"
        subgraph "Region: us-west2"
            subgraph "Cloud Run Services"
                FE[buildtrace-frontend<br/>1 vCPU, 512MB<br/>0-5 instances]
                BE[buildtrace-backend<br/>2 vCPU, 2GB<br/>1-10 instances]
            end

            subgraph "Cloud SQL"
                DB[(buildtrace-dev-db<br/>PostgreSQL 17<br/>db-perf-optimized-N-8)]
            end

            subgraph "Cloud Storage"
                Input[buildtrace-dev-input<br/>Uploaded drawings]
                Processed[buildtrace-dev-processed<br/>Results & overlays]
                Artifacts[buildtrace-dev-artifacts<br/>Build artifacts]
                Logs[buildtrace-dev-logs<br/>Application logs]
            end

            subgraph "Pub/Sub"
                OCRTopic[ocr-queue topic]
                DiffTopic[diff-queue topic]
                SummaryTopic[summary-queue topic]
                OCRDLQ[ocr-dlq topic]
                DiffDLQ[diff-dlq topic]
                SummaryDLQ[summary-dlq topic]
            end
        end

        subgraph "Global Services"
            SecretMgr[Secret Manager<br/>6 secrets]
            IAM[IAM<br/>Service Accounts]
            CloudLog[Cloud Logging]
        end
    end

    FE --> BE
    BE --> DB
    BE --> Input
    BE --> Processed
    BE --> OCRTopic
    BE --> SecretMgr

    OCRTopic --> Processed
    DiffTopic --> Processed
    SummaryTopic --> DB
```

### 2.2 Container Architecture

```mermaid
graph LR
    subgraph "Frontend Container"
        NextJS[Next.js App]
        NodeJS[Node.js 18]
        PM2[PM2 Process Manager]
    end

    subgraph "Backend Container"
        Flask[Flask App]
        Gunicorn[Gunicorn WSGI]
        Python[Python 3.11]
    end

    subgraph "Worker Container"
        Worker[Worker Script]
        PubSubClient[Pub/Sub Client]
        AIClient[AI SDK]
    end

    NextJS --> NodeJS
    NodeJS --> PM2

    Flask --> Gunicorn
    Gunicorn --> Python

    Worker --> PubSubClient
    Worker --> AIClient
```

---

## 3. Component Architecture

### 3.1 Backend Component Diagram

```mermaid
graph TB
    subgraph "Flask Application"
        App[app.py<br/>Entry Point]
        Config[config.py<br/>Configuration]
        
        subgraph "Blueprints (API Routes)"
            AuthBP[auth.py<br/>/api/v1/auth/*]
            JobsBP[jobs.py<br/>/api/v1/jobs/*]
            DrawingsBP[drawings.py<br/>/api/v1/drawings/*]
            ProjectsBP[projects.py<br/>/api/v1/projects/*]
            OverlaysBP[overlays.py<br/>/api/v1/overlays/*]
            SummariesBP[summaries.py<br/>/api/v1/summaries/*]
            ChatBP[chat.py<br/>/api/v1/chat/*]
        end

        subgraph "Services (Business Logic)"
            Orchestrator[orchestrator.py<br/>Job Orchestration]
            DrawingService[drawing_service.py<br/>Upload Handling]
            ChatService[chatbot_service.py<br/>AI Chatbot]
            PageExtractor[page_extractor.py<br/>PDF Processing]
        end

        subgraph "Processing (ML Pipelines)"
            OCRPipeline[ocr_pipeline.py<br/>Text Extraction]
            DiffPipeline[diff_pipeline.py<br/>Change Detection]
            SummaryPipeline[summary_pipeline.py<br/>AI Summary]
            ChangeAnalyzer[change_analyzer.py<br/>Analysis Logic]
        end

        subgraph "GCP Integration"
            Database[database.py<br/>Cloud SQL]
            Storage[storage_service.py<br/>Cloud Storage]
            PubSub[publisher.py<br/>Cloud Pub/Sub]
        end

        subgraph "Utilities"
            PDFParser[pdf_parser.py]
            ImageUtils[image_utils.py]
            JWTUtils[jwt_utils.py]
            AuthHelpers[auth_helpers.py]
        end
    end

    App --> Config
    App --> AuthBP
    App --> JobsBP
    App --> DrawingsBP

    JobsBP --> Orchestrator
    DrawingsBP --> DrawingService
    ChatBP --> ChatService

    Orchestrator --> PubSub
    Orchestrator --> Database

    DrawingService --> Storage
    DrawingService --> PageExtractor

    PageExtractor --> PDFParser
    PageExtractor --> Storage
```

### 3.2 Frontend Component Diagram

```mermaid
graph TB
    subgraph "Next.js Application"
        subgraph "Pages (App Router)"
            HomePage[page.tsx<br/>/ (Upload)]
            LoginPage[login/page.tsx<br/>/login]
            ResultsPage[results/page.tsx<br/>/results]
            ProjectsPage[projects/page.tsx<br/>/projects]
            ProjectDetail[projects/[id]/page.tsx<br/>/projects/:id]
        end

        subgraph "Components"
            subgraph "Auth"
                LoginBtn[LoginButton.tsx]
                ProtectedRoute[ProtectedRoute.tsx]
            end

            subgraph "Layout"
                Header[Header.tsx]
            end

            subgraph "Upload"
                FileUploader[FileUploader.tsx]
                ProcessingMonitor[ProcessingMonitor.tsx]
                ProgressSteps[ProgressSteps.tsx]
                RecentSessions[RecentSessions.tsx]
            end

            subgraph "Results"
                OverlayViewer[OverlayImageViewer.tsx]
                ChangesList[ChangesList.tsx]
                SummaryPanel[SummaryPanel.tsx]
                ViewModeToggle[ViewModeToggle.tsx]
            end

            subgraph "Reports"
                CostReport[CostImpactReport.tsx]
                ScheduleReport[ScheduleImpactReport.tsx]
            end
        end

        subgraph "State & API"
            AuthStore[authStore.ts<br/>Zustand]
            APIClient[api.ts<br/>Axios]
            MockAPI[mockApiClient.ts]
        end

        subgraph "Types"
            Types[types/index.ts]
        end
    end

    HomePage --> FileUploader
    HomePage --> ProcessingMonitor
    HomePage --> RecentSessions

    ResultsPage --> OverlayViewer
    ResultsPage --> ChangesList
    ResultsPage --> SummaryPanel
    ResultsPage --> CostReport
    ResultsPage --> ScheduleReport

    FileUploader --> APIClient
    OverlayViewer --> APIClient
    LoginBtn --> AuthStore
    ProtectedRoute --> AuthStore

    APIClient --> MockAPI
```

---

## 4. Backend Architecture

### 4.1 Request Flow

```mermaid
graph LR
    Client[Client] --> CORS[CORS<br/>Middleware]
    CORS --> Auth[Auth<br/>Middleware]
    Auth --> Blueprint[Blueprint<br/>Route Handler]
    Blueprint --> Service[Service<br/>Layer]
    Service --> Repository[Database<br/>Layer]
    Repository --> DB[(PostgreSQL)]
    Service --> Storage[Storage<br/>Layer]
    Storage --> GCS[(GCS)]
```

### 4.2 Blueprint Organization

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `auth` | `/api/v1/auth` | Authentication (Google OAuth) |
| `jobs` | `/api/v1/jobs` | Job management |
| `drawings` | `/api/v1/drawings` | Drawing uploads |
| `projects` | `/api/v1/projects` | Project management |
| `overlays` | `/api/v1/overlays` | Overlay images |
| `summaries` | `/api/v1/summaries` | AI summaries |
| `chat` | `/api/v1/chat` | Chatbot |
| `sessions` | `/api/v1/sessions` | Legacy sessions |

### 4.3 Service Layer Pattern

```mermaid
classDiagram
    class OrchestratorService {
        +pubsub: PubSubPublisher
        +create_streaming_job()
        +create_comparison_job()
        +on_page_ocr_complete()
        +on_page_diff_complete()
        +on_page_summary_complete()
    }

    class DrawingUploadService {
        +storage: StorageService
        +handle_upload()
        +validate_file()
        +create_drawing_version()
    }

    class ChatbotService {
        +client: GeminiClient
        +send_message()
        +get_session_context()
        +search_web()
    }

    class PageExtractorService {
        +storage: StorageService
        +extract_pages()
        +convert_pdf_to_png()
    }

    OrchestratorService --> PageExtractorService
    DrawingUploadService --> OrchestratorService
```

---

## 5. Frontend Architecture

### 5.1 State Management

```mermaid
graph TB
    subgraph "Zustand Store"
        AuthStore[authStore<br/>- user<br/>- token<br/>- isAuthenticated]
    end

    subgraph "Component State"
        LocalState[useState<br/>- form data<br/>- UI state]
    end

    subgraph "Server State"
        APIState[API Responses<br/>- job status<br/>- results]
    end

    AuthStore --> ProtectedRoute
    AuthStore --> Header
    LocalState --> UploadPage
    LocalState --> ResultsPage
    APIState --> ProcessingMonitor
    APIState --> ResultsPage
```

### 5.2 API Client Pattern

```mermaid
classDiagram
    class UnifiedApiClient {
        <<interface>>
        +googleLogin()
        +logout()
        +getCurrentUser()
        +listProjects()
        +uploadDrawing()
        +getJob()
        +getJobProgress()
        +getJobResults()
        +getOverlayImageUrl()
    }

    class ApiClient {
        -client: AxiosInstance
        +get()
        +post()
        +put()
        +delete()
        +uploadFiles()
    }

    class MockApiClient {
        -delay()
        -respond()
        +getJob()
        +getJobProgress()
    }

    UnifiedApiClient <|.. ApiClient
    UnifiedApiClient <|.. MockApiClient
```

---

## 6. Database Architecture

### 6.1 Entity Relationship Diagram

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : contains
    ORGANIZATIONS ||--o{ PROJECTS : owns

    USERS ||--o{ PROJECTS : creates
    USERS ||--o{ JOBS : creates
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ AUDIT_LOGS : generates

    PROJECTS ||--o{ DRAWING_VERSIONS : contains
    PROJECTS ||--o{ JOBS : has

    SESSIONS ||--o{ DRAWINGS : contains
    SESSIONS ||--o{ COMPARISONS : produces
    SESSIONS ||--o{ CHAT_CONVERSATIONS : has

    DRAWINGS ||--o{ DRAWING_VERSIONS : tracks

    JOBS ||--o{ JOB_STAGES : has
    JOBS ||--|| DIFF_RESULTS : produces

    DIFF_RESULTS ||--o{ MANUAL_OVERLAYS : has
    DIFF_RESULTS ||--o{ CHANGE_SUMMARIES : has

    CHAT_CONVERSATIONS ||--o{ CHAT_MESSAGES : contains
```

### 6.2 Table Groups

```mermaid
graph TB
    subgraph "Identity"
        users
        organizations
        oauth
    end

    subgraph "Project Management"
        projects
        project_users
    end

    subgraph "Drawing Management"
        drawings
        drawing_versions
        sessions
    end

    subgraph "Job Processing"
        jobs
        job_stages
    end

    subgraph "Results"
        diff_results
        manual_overlays
        change_summaries
    end

    subgraph "Communication"
        chat_conversations
        chat_messages
    end

    subgraph "Audit"
        audit_logs
    end

    subgraph "Legacy"
        comparisons
        analysis_results
        processing_jobs
    end
```

---

## 7. Message Queue Architecture

### 7.1 Pub/Sub Topology

```mermaid
graph TB
    subgraph "Publishers"
        Backend[Backend API]
        OCRWorker[OCR Worker]
        DiffWorker[Diff Worker]
    end

    subgraph "Topics"
        OCRTopic[ocr-queue]
        DiffTopic[diff-queue]
        SummaryTopic[summary-queue]
        OCRDLQ[ocr-dlq]
        DiffDLQ[diff-dlq]
        SummaryDLQ[summary-dlq]
    end

    subgraph "Subscriptions"
        OCRSub[ocr-worker-sub<br/>max_delivery: 5]
        DiffSub[diff-worker-sub<br/>max_delivery: 5]
        SummarySub[summary-worker-sub<br/>max_delivery: 5]
    end

    subgraph "Workers"
        OCRConsumer[OCR Worker]
        DiffConsumer[Diff Worker]
        SummaryConsumer[Summary Worker]
    end

    Backend --> OCRTopic
    OCRWorker --> DiffTopic
    DiffWorker --> SummaryTopic

    OCRTopic --> OCRSub
    DiffTopic --> DiffSub
    SummaryTopic --> SummarySub

    OCRSub --> OCRConsumer
    DiffSub --> DiffConsumer
    SummarySub --> SummaryConsumer

    OCRSub -.->|failed| OCRDLQ
    DiffSub -.->|failed| DiffDLQ
    SummarySub -.->|failed| SummaryDLQ
```

### 7.2 Message Flow

```mermaid
sequenceDiagram
    participant Backend
    participant OCRQueue as OCR Topic
    participant OCRWorker as OCR Worker
    participant DiffQueue as Diff Topic
    participant DiffWorker as Diff Worker
    participant SummaryQueue as Summary Topic
    participant SummaryWorker as Summary Worker

    Backend->>OCRQueue: publish(job_id, page_number)
    OCRQueue->>OCRWorker: deliver message
    OCRWorker->>OCRWorker: process OCR
    OCRWorker->>DiffQueue: publish(job_id, page_number, ocr_refs)
    OCRWorker-->>OCRQueue: ack

    DiffQueue->>DiffWorker: deliver message
    DiffWorker->>DiffWorker: process diff
    DiffWorker->>SummaryQueue: publish(job_id, page_number, diff_id)
    DiffWorker-->>DiffQueue: ack

    SummaryQueue->>SummaryWorker: deliver message
    SummaryWorker->>SummaryWorker: generate summary
    SummaryWorker-->>SummaryQueue: ack
```

---

## 8. Security Architecture

### 8.1 Authentication Flow

```mermaid
graph TB
    subgraph "Client"
        Browser[Browser]
    end

    subgraph "Identity Provider"
        Google[Google OAuth 2.0]
    end

    subgraph "Application"
        Frontend[Frontend]
        Backend[Backend]
    end

    subgraph "Security Components"
        JWT[JWT Token]
        Session[Session Cookie]
        SecretMgr[Secret Manager]
    end

    Browser -->|1. Login click| Frontend
    Frontend -->|2. Redirect| Google
    Google -->|3. Auth code| Backend
    Backend -->|4. Exchange code| Google
    Google -->|5. Access token| Backend
    Backend -->|6. Create session| Session
    Backend -->|7. Issue JWT| JWT
    JWT -->|8. Return to client| Browser
    Browser -->|9. API calls + JWT| Backend
    Backend -->|10. Validate| SecretMgr
```

### 8.2 Security Layers

```mermaid
graph TB
    subgraph "Network Security"
        TLS[TLS 1.3 Encryption]
        CORS[CORS Policy]
        Firewall[VPC Firewall]
    end

    subgraph "Application Security"
        OAuth[OAuth 2.0]
        JWT[JWT Validation]
        InputVal[Input Validation]
    end

    subgraph "Data Security"
        EncRest[Encryption at Rest]
        EncTransit[Encryption in Transit]
        Secrets[Secret Manager]
    end

    subgraph "Access Control"
        IAM[IAM Roles]
        RBAC[User Ownership]
        SvcAcct[Service Accounts]
    end

    TLS --> OAuth
    CORS --> JWT
    OAuth --> IAM
    JWT --> RBAC
    Secrets --> EncRest
    EncTransit --> Firewall
```

### 8.3 Service Account Permissions

| Service Account | Permissions |
|-----------------|-------------|
| `buildtrace-service-account` | Cloud SQL Client, Storage Object Admin, Pub/Sub Publisher/Subscriber, Secret Manager Accessor |
| `frontend-service-account` | Cloud Run Invoker |

---

*End of Architecture Diagrams Document*

