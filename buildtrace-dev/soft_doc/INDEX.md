# BuildTrace Software Documentation

**Version:** 2.0.0  
**Last Updated:** December 2025  
**Status:** Production-Ready ✅

---

## 📚 Documentation Index

This folder contains comprehensive software documentation for the BuildTrace platform.

### Core Documents

| Document | Description |
|----------|-------------|
| [SRS.md](./SRS.md) | Software Requirements Specification |
| [USE_CASE_DIAGRAMS.md](./USE_CASE_DIAGRAMS.md) | Use Case Diagrams with Actor Analysis |
| [SEQUENCE_DIAGRAMS.md](./SEQUENCE_DIAGRAMS.md) | Sequence Diagrams for Key Flows |
| [ACTIVITY_DIAGRAMS.md](./ACTIVITY_DIAGRAMS.md) | Activity Diagrams for Processes |
| [DFD.md](./DFD.md) | Data Flow Diagrams (Level 0, 1, 2) |
| [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md) | System Architecture & Flow Diagrams |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Complete Database Schema Documentation |
| [API_REFERENCE.md](./API_REFERENCE.md) | REST API Reference |

---

## 🎯 Project Overview

**BuildTrace** is a cloud-native SaaS platform for **automated construction drawing comparison and change detection**. The system leverages AI-powered OCR, computer vision, and Large Language Models (LLMs) to identify, visualize, and summarize changes between drawing versions.

### Key Capabilities

1. **Automated PDF Comparison** - Upload two versions of construction drawings
2. **AI-Powered OCR** - Extract text and layout using Google Gemini Vision
3. **Change Detection** - Identify additions, deletions, and modifications
4. **Visual Overlay** - Generate color-coded overlay images
5. **AI Summarization** - Natural language summaries of changes
6. **Real-time Processing** - Asynchronous job processing with streaming results
7. **Multi-tenant Support** - Organization-based project management

---

## 🏗️ Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT TIER                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Next.js 14 Frontend (React/TypeScript/TailwindCSS)           │  │
│  │  - Authentication (Google OAuth 2.0)                          │  │
│  │  - File Upload Interface                                      │  │
│  │  - Real-time Processing Monitor                               │  │
│  │  - Results Visualization with Overlay Viewer                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTPS/REST API
┌────────────────────────────────┴────────────────────────────────────┐
│                         APPLICATION TIER                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Flask Backend API (Python 3.11)                              │  │
│  │  - RESTful API Endpoints (Blueprints)                         │  │
│  │  - OAuth 2.0 + JWT Authentication                             │  │
│  │  - Job Orchestration Service                                  │  │
│  │  - AI Chatbot Service                                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐    ┌───────────────────┐    ┌───────────────────┐
│  Cloud SQL    │    │  Cloud Storage    │    │  Cloud Pub/Sub    │
│  PostgreSQL   │    │  (GCS Buckets)    │    │  (Message Queue)  │
└───────────────┘    └───────────────────┘    └─────────┬─────────┘
                                                        │
                              ┌──────────────────────────┼──────────────────────────┐
                              │                          │                          │
                              ▼                          ▼                          ▼
                    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
                    │   OCR Worker     │    │   Diff Worker    │    │  Summary Worker  │
                    │  (Gemini Vision) │    │  (OpenCV/SIFT)   │    │  (Gemini 2.5)    │
                    └──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## 🛠️ Technology Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript 5.x
- **UI Library:** React 18.x
- **Styling:** TailwindCSS 3.x
- **State Management:** Zustand 4.x
- **HTTP Client:** Axios 1.x

### Backend
- **Framework:** Flask 3.x
- **Language:** Python 3.11
- **ORM:** SQLAlchemy 2.x
- **Server:** Gunicorn 21.x

### AI/ML
- **Primary AI:** Google Gemini 2.5 Pro (Vision + Text)
- **Fallback AI:** OpenAI GPT-5
- **Image Processing:** OpenCV 4.x, Pillow 10.x
- **PDF Processing:** pdf2image, PyPDF2

### Infrastructure (Google Cloud Platform)
- **Compute:** Cloud Run (Serverless)
- **Database:** Cloud SQL (PostgreSQL 17)
- **Storage:** Cloud Storage (GCS)
- **Messaging:** Cloud Pub/Sub
- **Secrets:** Secret Manager
- **Logging:** Cloud Logging
- **IAM:** Service Accounts

---

## 📊 System Metrics

| Metric | Value |
|--------|-------|
| Max File Size | 70 MB |
| Supported Formats | PDF, DWG, DXF, PNG, JPG |
| Average Processing Time | 2-5 minutes (2-page PDF) |
| Streaming Results | Per-page updates |
| Database | PostgreSQL 17 |
| Concurrent Jobs | Limited by Cloud Run instances |

---

## 📁 Repository Structure

```
buildtrace-dev/
├── backend/                    # Flask API Backend
│   ├── app.py                 # Application entry point
│   ├── config.py              # Configuration management
│   ├── blueprints/            # API route handlers
│   ├── services/              # Business logic layer
│   ├── workers/               # Pub/Sub message processors
│   ├── processing/            # Core ML pipelines
│   ├── gcp/                   # GCP service integrations
│   └── utils/                 # Utility functions
├── frontend/                   # Next.js Frontend
│   └── src/
│       ├── app/               # Next.js App Router pages
│       ├── components/        # React components
│       ├── lib/               # API client
│       ├── mocks/             # Mock data for development
│       ├── store/             # Zustand state
│       └── types/             # TypeScript definitions
├── docs/                       # Developer documentation
├── scripts/                    # Deployment & utility scripts
├── k8s/                        # Kubernetes manifests
├── soft_doc/                   # Software documentation (this folder)
├── ARCHITECTURE.md             # Architecture overview
├── README.md                   # Project README
└── docker-compose.yml          # Local development setup
```

---

## 🔗 Quick Links

- **Production Frontend:** https://buildtrace-frontend-136394139608.us-west2.run.app
- **Production Backend:** https://buildtrace-backend-136394139608.us-west2.run.app
- **Health Check:** https://buildtrace-backend-136394139608.us-west2.run.app/health
- **GCP Console:** https://console.cloud.google.com/home/dashboard?project=buildtrace-dev

---

## 📝 Document Conventions

- **Diagrams:** All diagrams use Mermaid syntax for GitHub rendering
- **Code Examples:** Inline code uses backticks, blocks use triple backticks
- **API Endpoints:** Documented with HTTP method, path, and JSON examples
- **Status Icons:** ✅ Complete, ⚠️ Partial, ❌ Not Implemented

---

**Prepared by:** Senior Software Engineer  
**Document Version:** 1.0  

