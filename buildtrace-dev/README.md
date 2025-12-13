# BuildTrace Dev

**Version:** 2.0.0 | **Status:** Production-Ready ✅

Drawing comparison and change detection system for architectural drawings. BuildTrace is a cloud-native SaaS platform that uses AI-powered OCR, computer vision, and LLM analysis to identify, visualize, and summarize changes between construction drawing versions.

## 📚 Documentation

### 📋 Software Documentation (NEW!)

Complete software engineering documentation in **[soft_doc/](./soft_doc/INDEX.md)**:

| Document | Description |
|----------|-------------|
| **[SRS.md](./soft_doc/SRS.md)** | Software Requirements Specification |
| **[USE_CASE_DIAGRAMS.md](./soft_doc/USE_CASE_DIAGRAMS.md)** | Use Case Diagrams with Actor Analysis |
| **[SEQUENCE_DIAGRAMS.md](./soft_doc/SEQUENCE_DIAGRAMS.md)** | Sequence Diagrams for Key Flows |
| **[ACTIVITY_DIAGRAMS.md](./soft_doc/ACTIVITY_DIAGRAMS.md)** | Activity Diagrams for Processes |
| **[DFD.md](./soft_doc/DFD.md)** | Data Flow Diagrams (Level 0, 1, 2) |
| **[ARCHITECTURE_DIAGRAMS.md](./soft_doc/ARCHITECTURE_DIAGRAMS.md)** | System Architecture & Component Diagrams |
| **[DATABASE_SCHEMA.md](./soft_doc/DATABASE_SCHEMA.md)** | Complete Database Schema Documentation |
| **[API_REFERENCE.md](./soft_doc/API_REFERENCE.md)** | REST API Reference |

### Core Documentation
- **[docs/SYSTEM_OVERVIEW.md](./docs/SYSTEM_OVERVIEW.md)** - Complete system overview and repository structure
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed system architecture
- **[ANALYSIS.md](./ANALYSIS.md)** - Codebase analysis and improvements
- **[Advanced_next_rag_build_plan.md](./Advanced_next_rag_build_plan.md)** - ⭐ **NEW: Advanced RAG Implementation Plan** (OpenAI Tool Calling + pgvector)
- **[plan_gcp_rag.md](./plan_gcp_rag.md)** - Original RAG architecture plan
- **[docs/PROGRESS.md](./docs/PROGRESS.md)** - Implementation status and progress
- **[docs/PENDING.md](./docs/PENDING.md)** - Remaining tasks and priorities
- **[docs/FLOW_DIAGRAM.md](./docs/FLOW_DIAGRAM.md)** - Complete data flow diagrams
- **[docs/README.md](./docs/README.md)** - Documentation index

### Deployment & Operations
- **[docs/deployment/QUICK_DEPLOY.md](./docs/deployment/QUICK_DEPLOY.md)** - Quick deployment reference
- **[docs/deployment/DEPLOYMENT_GUIDE.md](./docs/deployment/DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[docs/deployment/DEPLOYMENT_CHECKLIST.md](./docs/deployment/DEPLOYMENT_CHECKLIST.md)** - Deployment checklist
- **[docs/deployment/FINAL_IMAGE_PULL_FIX.md](./docs/deployment/FINAL_IMAGE_PULL_FIX.md)** - Image pull troubleshooting
- **[k8s/README.md](./k8s/README.md)** - Kubernetes worker deployment

### Setup & Configuration
- **[docs/setup/ADD_GEMINI_SECRET.md](./docs/setup/ADD_GEMINI_SECRET.md)** - Gemini secret setup
- **[docs/setup/CLI_SECRET_SETUP.md](./docs/setup/CLI_SECRET_SETUP.md)** - CLI secret setup
- **[docs/setup/OAUTH_SETUP.md](./docs/setup/OAUTH_SETUP.md)** - OAuth setup guide

### Features
- **[docs/features/BOUNDING_BOX_ENHANCEMENT.md](./docs/features/BOUNDING_BOX_ENHANCEMENT.md)** - Bounding box feature
- **[docs/features/OCR_ENHANCEMENT.md](./docs/features/OCR_ENHANCEMENT.md)** - OCR enhancements
- **[docs/features/OUTPUT_LOCATIONS.md](./docs/features/OUTPUT_LOCATIONS.md)** - Output locations reference

### Status & History
- **[docs/DONE.md](./docs/DONE.md)** - Completed work and features
- **[docs/PLANNED.md](./docs/PLANNED.md)** - Future features and enhancements

## 🚀 Quick Start

### Local Development

```bash
# Start all services
docker-compose up

# Backend: http://localhost:5001
# Frontend: http://localhost:3000
```

### GCP Deployment

```bash
# Deploy both backend and frontend
./scripts/deploy-all.sh

# Or deploy individually
./scripts/deploy-frontend.sh                    # Frontend only
DEPLOY_FRONTEND=false ./scripts/DEPLOY_AND_TEST.sh  # Backend only
```

See [docs/deployment/QUICK_DEPLOY.md](./docs/deployment/QUICK_DEPLOY.md) for quick reference or [docs/deployment/DEPLOYMENT_GUIDE.md](./docs/deployment/DEPLOYMENT_GUIDE.md) for complete documentation.

## 📋 Project Status

- ✅ **Development**: Complete
- ✅ **Deployment**: Configured and ready
- ✅ **Testing**: Available

## 🔗 Links

- **Backend API:** https://buildtrace-backend-136394139608.us-west2.run.app
- **Frontend:** https://buildtrace-frontend-136394139608.us-west2.run.app

## 📝 Recent Changes

### 2025-12-12: Advanced RAG Implementation Plan (Updated with Gemini 3 Pro)

Added comprehensive **Advanced RAG Build Plan** for next-generation question-answering:

| Component | Technology | Status |
|-----------|-----------|--------|
| **Agentic Pipeline** | Gemini Function Calling | ✅ Planned |
| **Vector Database** | pgvector on Cloud SQL | ✅ Decided |
| **Embeddings** | text-embedding-3-small | ✅ Planned |
| **Intent Classification** | Gemini 3 Pro | ✅ Planned |
| **Agentic Planning** | Gemini 3 Pro | ✅ Planned |
| **Answer Generation** | Gemini 3 Pro Vision | ✅ Planned |
| **Implementation** | 7-week phased approach | 📋 Ready |

**Key Features:**
- Natural language Q&A over architectural drawings
- Multi-region vector search with smart routing
- <8s P95 latency, **<$0.012 per query** (4x cheaper than GPT-4o)
- 90%+ accuracy on test set
- **Best-in-class vision** (81% MMMU-Pro benchmark, Nov 2025)
- **1M token context window** (5x larger than competitors)

**Why Gemini 3 Pro:**
- 60% cheaper than Claude Opus 4.5 ($2/1M vs $5/1M)
- Already using Gemini 2.5 Pro for OCR (easy migration)
- Native GCP integration via Vertex AI

See **[Advanced_next_rag_build_plan.md](./Advanced_next_rag_build_plan.md)** for full details.

### 2025-12-01: Sync with buildtrace-overlay-

Synchronized key components with `buildtrace-overlay-` for consistent behavior:

| Component | Status | Details |
|-----------|--------|---------|
| **Overlay Colors** | ✅ Synced | Light red (100,100,255), Light green (100,255,100), Gray (150,150,150) |
| **Overlay Algorithm** | ✅ Synced | Simple mask-based approach, same as buildtrace-overlay- |
| **Change Analyzer** | ✅ Synced | Same Gemini prompts (5-section analysis) |
| **Summary Pipeline** | ✅ Synced | Same OpenAI prompts for summary generation |
| **Chatbot Service** | ✅ Synced | Web search via DuckDuckGo + same system prompt |
| **PDF Layer Overlay** | ❌ Not Needed | Per user request |

**Files Modified:**
- `backend/utils/image_utils.py` - Overlay color palette
- `backend/processing/change_analyzer.py` - AI prompts synced
- `backend/processing/summary_pipeline.py` - Summary prompts synced
- `backend/services/chatbot_service.py` - Full rewrite with web search
- `backend/blueprints/chat.py` - Updated for new chatbot service

### 2025-11-29: Repository Organization
- Organized all files into appropriate folders
- Documentation moved to `docs/` with subdirectories
- Scripts consolidated in `scripts/` directory
- Logs moved to `logs/` directory
- See [docs/FILE_ORGANIZATION.md](./docs/FILE_ORGANIZATION.md) for structure

### 2025-11-28: Deployment Configuration Fixed
- Fixed deployment scripts to include frontend deployment
- Added flexible deployment options (deploy all, backend only, or frontend only)
- Created comprehensive deployment documentation
- Both backend and frontend now deploy automatically

### 2025-11-22: JWT Authentication Implementation
- Added JWT token support for cross-domain authentication
- Frontend now stores and sends JWT tokens automatically
- Backend accepts both JWT tokens and session cookies
- See [docs/DONE.md](./docs/DONE.md) for full details
