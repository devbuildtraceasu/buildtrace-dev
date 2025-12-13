# BuildTrace Codebase Analysis

**Last Updated:** December 1, 2025  
**Version:** 2.0.0+  
**Status:** Production Ready (with local development support)

---

## Executive Summary

BuildTrace is a cloud-native SaaS platform for automated construction drawing comparison and change detection. The codebase has been synchronized with `buildtrace-overlay-` for consistent overlay generation, AI prompts, and chatbot functionality.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Next.js 14 Frontend (TypeScript/React)                         │
│  - Google OAuth Authentication                                   │
│  - Drawing Upload Interface                                      │
│  - Real-time Processing Monitor                                  │
│  - Results Visualization (Overlay/Side-by-side)                 │
│  - Project Management UI                                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS/REST
┌──────────────────────┴──────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  Flask Backend API (Python 3.11)                                │
│  - RESTful API Endpoints                                        │
│  - OAuth 2.0 + JWT Authentication                               │
│  - Job Orchestration                                            │
│  - AI-powered Chatbot with Web Search                           │
└──────┬─────────┬──────────┬──────────┬───────────┬─────────────┘
       │         │          │          │           │
┌──────┴────┐ ┌─┴────┐ ┌───┴────┐ ┌───┴────┐ ┌───┴───────┐
│ Cloud SQL │ │ GCS  │ │ Pub/Sub│ │Secrets │ │  Logging  │
│PostgreSQL │ │Storage│ │ Queue  │ │Manager │ │   & Mon   │
└───────────┘ └──────┘ └────────┘ └────────┘ └───────────┘
```

---

## Component Status

### Backend Components

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **Core API** | `app.py` | ✅ Working | Flask app with CORS, blueprints |
| **Image Utils** | `utils/image_utils.py` | ✅ Synced | Overlay generation (synced colors) |
| **Change Analyzer** | `processing/change_analyzer.py` | ✅ Synced | Gemini-based analysis (synced prompts) |
| **Summary Pipeline** | `processing/summary_pipeline.py` | ✅ Synced | AI summary generation |
| **Chatbot Service** | `services/chatbot_service.py` | ✅ Synced | OpenAI + Web Search |
| **Auth Helpers** | `utils/auth_helpers.py` | ✅ Fixed | JWT + Session auth decorator |
| **Projects API** | `blueprints/projects.py` | ✅ Working | Project CRUD + stats |
| **Jobs API** | `blueprints/jobs.py` | ✅ Working | Job management |
| **Chat API** | `blueprints/chat.py` | ✅ Working | Chatbot endpoints |

### Frontend Components

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **API Client** | `lib/api.ts` | ✅ Fixed | Unified type for mock/real API |
| **Mock API** | `mocks/mockApiClient.ts` | ✅ Updated | Full mock implementation |
| **Projects Page** | `app/projects/page.tsx` | ✅ Working | Project list/create |
| **Project Detail** | `app/projects/[id]/page.tsx` | ✅ Working | Documents, drawings, comparisons |
| **Results Page** | `components/pages/ResultsPage.tsx` | ✅ Working | Comparison results viewer |
| **Overlay Viewer** | `components/results/OverlayImageViewer.tsx` | ✅ Working | Synchronized pan/zoom |

---

## Sync with buildtrace-overlay-

### Overlay Colors (BGR Format)

| Element | buildtrace-overlay- | buildtrace-dev | Status |
|---------|---------------------|----------------|--------|
| Removed (old only) | `(100, 100, 255)` | `(100, 100, 255)` | ✅ Synced |
| Added (new only) | `(100, 255, 100)` | `(100, 255, 100)` | ✅ Synced |
| Unchanged | `(150, 150, 150)` | `(150, 150, 150)` | ✅ Synced |
| Background | `(255, 255, 255)` | `(255, 255, 255)` | ✅ Synced |

### Change Analyzer Prompts

Both systems now use identical analysis prompts:

```python
# System Prompt
"""You are an expert project manager at a general contractor company with access 
to document search and web research tools. Analyze the provided architectural 
drawings thoroughly and identify all changes between the old and new versions.
Focus on practical construction implications and cost impacts."""

# Analysis Sections
1. Most Critical Change
2. Complete Change List  
3. Change Format (Aspect + Action + Detail + Location)
4. Construction Impact
5. Recommendations
```

### Chatbot Features

| Feature | buildtrace-overlay- | buildtrace-dev | Status |
|---------|---------------------|----------------|--------|
| System Prompt | ✅ | ✅ | Identical |
| Web Search | ✅ DuckDuckGo | ✅ DuckDuckGo | Synced |
| Session Context | ✅ | ✅ | Both DB + file fallback |
| Suggested Questions | ✅ | ✅ | Context-aware |
| Conversation History | ✅ (10 msgs) | ✅ (10 msgs) | Synced |

---

## Code Assumptions & Risks

### High Risk
| Assumption | Location | Mitigation |
|------------|----------|------------|
| OpenAI API key required for chatbot | `chatbot_service.py:66` | Returns fallback suggestions when unavailable |
| Job model has `session_id` | `chatbot_service.py:175` | May need schema migration |

### Medium Risk
| Assumption | Location | Mitigation |
|------------|----------|------------|
| Images have white background (>240 gray) | `image_utils.py:67` | Works for most architectural drawings |
| GCS paths normalized | `storage_service.py` | Already fixed |

### Low Risk
| Assumption | Location | Mitigation |
|------------|----------|------------|
| PDF pages sequential | `ocr_pipeline.py` | Standard assumption |
| Mock job-001 always exists | `mockApiClient.ts` | Dev only |

---

## API Endpoints

### Chat API (New)
```
POST /api/v1/chat/sessions/<session_id>
  - Send chat message with session context
  - Requires authentication

GET /api/v1/chat/sessions/<session_id>/suggested
  - Get suggested questions (no auth required)
  - Returns fallback if chatbot unavailable

GET /api/v1/chat/sessions/<session_id>/history
  - Get conversation history
  - Requires authentication

POST /api/v1/chat/web-search
  - Perform web search for construction info
```

### Project API (Enhanced)
```
GET /api/v1/projects/<project_id>/documents
GET /api/v1/projects/<project_id>/drawings
GET /api/v1/projects/<project_id>/comparisons
GET /api/v1/projects/<project_id>/stats
```

---

## Environment Variables

### Required for Chatbot
```bash
OPENAI_API_KEY=sk-...      # Required for chatbot
OPENAI_MODEL=gpt-4o        # Default model
```

### Required for Change Analyzer
```bash
GEMINI_API_KEY=...         # Required for change analysis
GEMINI_MODEL=models/gemini-2.5-pro
```

### Optional
```bash
NEXT_PUBLIC_USE_MOCKS=true  # Enable mock mode for frontend
```

---

## Known Issues

1. **Chatbot requires API keys** - Returns fallback when keys unavailable
2. **Database migrations** - May fail in Docker if DB not ready
3. **TypeScript union types** - Fixed with type assertions

---

## Testing

### Run Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Test Chatbot Endpoint
```bash
curl http://localhost:5001/api/v1/chat/sessions/test/suggested
```

### Test Health
```bash
curl http://localhost:5001/health
```

---

## Files Modified (Dec 1, 2025)

### Backend
- `backend/utils/image_utils.py` - Overlay colors synced
- `backend/processing/change_analyzer.py` - AI prompts synced
- `backend/processing/summary_pipeline.py` - Summary prompts synced
- `backend/services/chatbot_service.py` - Full rewrite with web search
- `backend/blueprints/chat.py` - Updated for new chatbot
- `backend/utils/auth_helpers.py` - Added proper `require_auth` decorator

### Frontend
- `frontend/src/lib/api.ts` - Unified API client type
- `frontend/src/mocks/mockApiClient.ts` - Added missing methods
- `frontend/src/app/projects/page.tsx` - Fixed date formatting

---

## Future Improvements

1. **Add unit tests** for chatbot web search
2. **Implement token refresh** for long sessions
3. **Add rate limiting** for API endpoints
4. **Set up monitoring** dashboards
5. **Add CI/CD pipeline** for automated deployment

---

**Document Version:** 2.0.1  
**Prepared:** AI Assistant  
**Verified:** December 1, 2025
