# BuildTrace Architecture v4 - Part 1: Backend & Processing
## Codebase-Aware Next Version (Flask-Based with Page-Level Pub/Sub)

_Last updated: November 18, 2025_

This document provides a **codebase-specific architecture** for BuildTrace's next version, maintaining Flask as the core framework while implementing **page-by-page async processing** with Pub/Sub messaging for real-time progress updates.

---

## 1. Executive Summary

### 1.1 Current State Analysis

**Backend Status:**
- Flask-based monolith (`app.py`, `app_with_auth.py`)
- Complete processing pipeline implemented
- Dual storage support (local filesystem + GCS)
- Dual database support (file-based + PostgreSQL)
- Processing: Sync (default) with async capability via Cloud Tasks

**Frontend Status:**
- Two separate implementations:
  1. **demo-frontend**: React 18 + Vite + Express server + Supabase Auth
  2. **buildtrace-overlay-/frontend**: Next.js 14 + App Router
- Divergent database schemas and API contracts
- Independent deployment paths

**Key Challenges:**
1. Synchronous processing blocks request threads
2. Frontend-backend disconnect (different schemas, APIs)
3. No unified user/project management
4. No real-time progress feedback during processing
5. Two frontends create maintenance burden

### 1.2 Next Version Goals

1. ✅ **Keep Flask**: Maintain Flask for API service (team familiarity, proven stability)
2. ✅ **Page-by-Page Processing**: Each page pair comparison is a separate Pub/Sub message
3. ✅ **Real-Time Progress**: Stream results as each page completes via WebSocket
4. ✅ **Vertical Carousel**: Populate comparison results incrementally as pages complete
5. ✅ **Unified Frontend**: Single React-based frontend with project management
6. ✅ **Production-Ready**: GKE deployment with monitoring and auto-scaling

### 1.3 Why Keep Flask?

✅ **Team Familiarity**: Existing codebase is Flask-based, team knows it well  
✅ **Mature Ecosystem**: Flask-SocketIO for WebSocket, Flask-CORS for API  
✅ **Easy Migration**: Minimal code changes to existing endpoints  
✅ **Proven Stability**: Current system works, reduce migration risk  
✅ **Python Ecosystem**: Leverage existing Python libraries (OpenCV, PyMuPDF, etc.)

### 1.4 Key Architectural Innovation: Page-Level Pub/Sub

**Problem**: Multi-page PDFs take minutes to process, no progress feedback to user.

**Solution**: Break processing into **page-level messages**:
```
Upload PDF (10 pages) →
  OCR: 10 separate messages (one per page) →
  Matching: Group by drawing name →
  Diff: N messages (one per matched page pair) →
  Summary: N messages (one per overlay) →
  Real-time updates via WebSocket as each completes
```

**Benefits**:
- ✅ User sees progress immediately
- ✅ Results populate incrementally (vertical carousel)
- ✅ Failed pages don't block entire job
- ✅ Easier to scale workers per page
- ✅ Natural retry granularity

---

## 2. Architecture Overview

### 2.1 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  React Frontend (Unified)                                 │   │
│  │  - Project Management                                     │   │
│  │  - Drawing Upload & Version Tracking                     │   │
│  │  - Real-time Comparison Status (WebSocket)               │   │
│  │  - Vertical Carousel (populated incrementally)           │   │
│  │  - Manual Overlay Editing                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Flask API Service                                       │   │
│  │  - Flask-SocketIO for WebSocket                         │   │
│  │  - Authentication & Authorization                        │   │
│  │  - Project & Drawing Management                          │   │
│  │  - Job Creation & Status Queries                         │   │
│  │  - Manual Overlay Updates                                │   │
│  │  - Real-time Progress Broadcasting                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Queue Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Google Cloud Pub/Sub                                    │   │
│  │                                                           │   │
│  │  Topics:                                                  │   │
│  │  - ocr-pages-topic       (page-level OCR messages)      │   │
│  │  - diff-pairs-topic      (page-pair diff messages)      │   │
│  │  - summary-overlays-topic (overlay analysis messages)   │   │
│  │                                                           │   │
│  │  Subscriptions:                                          │   │
│  │  - ocr-worker-sub        → OCR Workers                   │   │
│  │  - diff-worker-sub       → Diff Workers                  │   │
│  │  - summary-worker-sub    → Summary Workers               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   OCR Worker     │ │   Diff Worker    │ │ Summary Worker   │
│   (Flask)        │ │   (Flask)        │ │   (Flask)        │
│                  │ │                  │ │                  │
│  Subscribes to:  │ │  Subscribes to:  │ │  Subscribes to:  │
│  ocr-pages-topic │ │  diff-pairs-topic│ │  summary-overlays│
│                  │ │                  │ │  -topic          │
│  Processes:      │ │  Processes:      │ │  Processes:      │
│  - 1 PDF page    │ │  - 1 page pair   │ │  - 1 overlay     │
│  - Extracts name │ │  - Alignment     │ │  - AI analysis   │
│  - Converts PNG  │ │  - Creates       │ │  - Change list   │
│                  │ │    overlay       │ │                  │
│  Publishes:      │ │  Publishes:      │ │  Publishes:      │
│  - Page complete │ │  - Pair complete │ │  - Summary ready │
│  - Triggers next │ │  - Triggers next │ │  - Final result  │
│    stage         │ │    stage         │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Orchestrator Service (Flask)                            │   │
│  │  - Listens to completion events                          │   │
│  │  - Manages job state machine                             │   │
│  │  - Triggers next stage when ready                        │   │
│  │  - Broadcasts progress via WebSocket                     │   │
│  │  - Handles retries and failures                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                  │
│  ┌─────────────────────┐         ┌──────────────────────────┐   │
│  │  PostgreSQL         │         │  Google Cloud Storage    │   │
│  │  (Cloud SQL)        │         │                          │   │
│  │  - Users            │         │  - Raw PDFs              │   │
│  │  - Projects         │         │  - Processed PNGs        │   │
│  │  - Sessions         │         │  - Overlays              │   │
│  │  - Drawings         │         │  - OCR JSON              │   │
│  │  - PageJobs         │         │  - Diff JSON             │   │
│  │  - Comparisons      │         │  - Manual overlays       │   │
│  │  - PageResults      │         │                          │   │
│  │  - ChangeSummaries  │         │                          │   │
│  └─────────────────────┘         └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Page-Level Processing Flow

```
USER UPLOADS PDF (5 pages old, 5 pages new)
              ↓
    ┌─────────────────────┐
    │  Flask API Service  │
    │  1. Store PDFs      │
    │  2. Create session  │
    │  3. Create drawings │
    │  4. Publish OCR msgs│
    └─────────────────────┘
              ↓
    ┌─────────────────────────────────────┐
    │ Pub/Sub: ocr-pages-topic            │
    │ Messages (10 total):                │
    │ - msg_1: {drawing_id: old, page: 0} │
    │ - msg_2: {drawing_id: old, page: 1} │
    │ - ...                                │
    │ - msg_6: {drawing_id: new, page: 0} │
    │ - ...                                │
    └─────────────────────────────────────┘
              ↓
    ┌─────────────────────┐
    │  OCR Workers (3x)   │
    │  Process in parallel│
    │  Each handles 1 page│
    └─────────────────────┘
              ↓
    Each page completion:
    1. Store result in DB (page_results table)
    2. Broadcast via WebSocket: {type: 'page_ocr_complete', page: 0}
    3. Frontend updates: "OCR: 1/10 pages complete"
              ↓
    ┌─────────────────────┐
    │  Orchestrator       │
    │  Detects: All OCR   │
    │  pages complete     │
    │  → Match drawings   │
    │  → Publish diff msgs│
    └─────────────────────┘
              ↓
    ┌─────────────────────────────────────┐
    │ Pub/Sub: diff-pairs-topic           │
    │ Messages (5 matched pairs):         │
    │ - msg_1: {old_page: 0, new_page: 0, │
    │           drawing_name: "A-101"}    │
    │ - msg_2: {old_page: 1, new_page: 1, │
    │           drawing_name: "A-102"}    │
    │ - ...                                │
    └─────────────────────────────────────┘
              ↓
    ┌─────────────────────┐
    │  Diff Workers (3x)  │
    │  Process pairs      │
    │  in parallel        │
    └─────────────────────┘
              ↓
    Each pair completion:
    1. Store overlay in GCS
    2. Store comparison in DB
    3. Broadcast: {type: 'pair_diff_complete', drawing_name: 'A-101'}
    4. Frontend: Populate carousel with A-101 result!
              ↓
    ┌─────────────────────────────────────┐
    │ Pub/Sub: summary-overlays-topic     │
    │ Messages (5 overlays):              │
    │ - msg_1: {comparison_id: xxx,       │
    │           overlay_path: ...}        │
    │ - ...                                │
    └─────────────────────────────────────┘
              ↓
    ┌─────────────────────┐
    │  Summary Workers    │
    │  (2x, rate-limited) │
    └─────────────────────┘
              ↓
    Each summary completion:
    1. Store in change_summaries table
    2. Broadcast: {type: 'summary_complete', drawing_name: 'A-101'}
    3. Frontend: Show summary in carousel card!
```

**Key Points**:
- 🔹 **10 OCR messages** (5 old + 5 new pages) processed in parallel
- 🔹 **5 Diff messages** (matched pairs) processed in parallel
- 🔹 **5 Summary messages** processed (rate-limited by OpenAI)
- 🔹 **Real-time updates** at each stage via WebSocket
- 🔹 **Vertical carousel** populates as each drawing completes

---

## 3. Backend Architecture (Flask-Based)

### 3.1 Flask API Service

**File**: `api_service.py` (enhanced from `app.py`)

```python
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from google.cloud import pubsub_v1
import json
import uuid
from datetime import datetime

# Import existing modules
from config import config
from gcp.storage import storage_service
from gcp.database import get_db_session
from gcp.database.models import (
    User, Project, Session, Drawing, PageJob, 
    Comparison, PageResult, ChangeSummary
)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
CORS(app)

# Initialize Flask-SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize Pub/Sub publisher
publisher = pubsub_v1.PublisherClient()
project_id = config.GCP_PROJECT_ID
ocr_topic_path = publisher.topic_path(project_id, 'ocr-pages-topic')
diff_topic_path = publisher.topic_path(project_id, 'diff-pairs-topic')
summary_topic_path = publisher.topic_path(project_id, 'summary-overlays-topic')

# ============================================================================
# AUTHENTICATION (keep existing logic)
# ============================================================================

def get_current_user():
    """Get current authenticated user (from Supabase JWT or Flask-Login)"""
    # Reuse existing auth logic from app_with_auth.py
    pass

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create new project"""
    user = get_current_user()
    data = request.json
    
    with get_db_session() as db:
        project = Project(
            user_id=user.id,
            name=data['name'],
            description=data.get('description'),
            project_number=data.get('project_number'),
            client_name=data.get('client_name'),
            location=data.get('location')
        )
        db.add(project)
        db.commit()
        
        return jsonify({
            'id': project.id,
            'name': project.name,
            'created_at': project.created_at.isoformat()
        }), 201

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List user's projects"""
    user = get_current_user()
    
    with get_db_session() as db:
        projects = db.query(Project).filter_by(user_id=user.id).all()
        
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'status': p.status,
            'created_at': p.created_at.isoformat()
        } for p in projects])

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details"""
    user = get_current_user()
    
    with get_db_session() as db:
        project = db.query(Project).filter_by(
            id=project_id, 
            user_id=user.id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        return jsonify({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'project_number': project.project_number,
            'client_name': project.client_name,
            'location': project.location,
            'status': project.status,
            'created_at': project.created_at.isoformat()
        })

# ============================================================================
# DRAWING VERSION MANAGEMENT
# ============================================================================

@app.route('/api/projects/<project_id>/drawings', methods=['POST'])
def upload_drawing_version(project_id):
    """Upload new drawing version"""
    user = get_current_user()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    drawing_name = request.form.get('drawing_name')  # e.g., "A-101"
    version_label = request.form.get('version_label')  # e.g., "Rev A"
    
    with get_db_session() as db:
        project = db.query(Project).filter_by(
            id=project_id, 
            user_id=user.id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get next version number
        existing_versions = db.query(DrawingVersion).filter_by(
            project_id=project_id,
            drawing_name=drawing_name
        ).count()
        
        version_number = existing_versions + 1
        
        # Store file in GCS
        storage_path = f"projects/{project_id}/drawings/{drawing_name}/v{version_number}/{file.filename}"
        storage_service.upload_file(file, storage_path)
        
        # Create drawing version record
        drawing_version = DrawingVersion(
            project_id=project_id,
            drawing_name=drawing_name,
            version_number=version_number,
            version_label=version_label,
            file_name=file.filename,
            storage_path=storage_path,
            uploaded_by=user.id
        )
        db.add(drawing_version)
        db.commit()
        
        return jsonify({
            'id': drawing_version.id,
            'drawing_name': drawing_name,
            'version_number': version_number,
            'version_label': version_label,
            'uploaded_at': drawing_version.upload_date.isoformat()
        }), 201

# ============================================================================
# COMPARISON CREATION (Enhanced with Page-Level Pub/Sub)
# ============================================================================

@app.route('/api/comparisons', methods=['POST'])
def create_comparison():
    """
    Create comparison job with page-level processing
    
    Request:
    {
        "project_id": "uuid",
        "old_drawing_version_id": "uuid",
        "new_drawing_version_id": "uuid"
    }
    
    Response:
    {
        "session_id": "uuid",
        "status": "processing",
        "total_pages_old": 5,
        "total_pages_new": 5,
        "websocket_room": "session_uuid"
    }
    """
    user = get_current_user()
    data = request.json
    
    project_id = data['project_id']
    old_version_id = data['old_drawing_version_id']
    new_version_id = data['new_drawing_version_id']
    
    with get_db_session() as db:
        # Verify project access
        project = db.query(Project).filter_by(
            id=project_id,
            user_id=user.id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get drawing versions
        old_version = db.query(DrawingVersion).get(old_version_id)
        new_version = db.query(DrawingVersion).get(new_version_id)
        
        if not old_version or not new_version:
            return jsonify({'error': 'Drawing version not found'}), 404
        
        # Create session
        session = Session(
            user_id=user.id,
            project_id=project_id,
            session_type='comparison',
            status='processing'
        )
        db.add(session)
        db.flush()
        
        # Create drawing records (for processing)
        old_drawing = Drawing(
            session_id=session.id,
            drawing_version_id=old_version_id,
            drawing_type='old',
            filename=old_version.file_name,
            storage_path=old_version.storage_path
        )
        new_drawing = Drawing(
            session_id=session.id,
            drawing_version_id=new_version_id,
            drawing_type='new',
            filename=new_version.file_name,
            storage_path=new_version.storage_path
        )
        db.add_all([old_drawing, new_drawing])
        db.flush()
        
        # Get page counts (by loading PDFs temporarily)
        import PyMuPDF as fitz
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            old_pdf_path = f"{temp_dir}/old.pdf"
            new_pdf_path = f"{temp_dir}/new.pdf"
            
            storage_service.download_file(old_version.storage_path, old_pdf_path)
            storage_service.download_file(new_version.storage_path, new_pdf_path)
            
            old_doc = fitz.open(old_pdf_path)
            new_doc = fitz.open(new_pdf_path)
            
            old_page_count = len(old_doc)
            new_page_count = len(new_doc)
            
            old_doc.close()
            new_doc.close()
        
        # Create page jobs for each page
        page_jobs = []
        
        # OCR jobs for old drawing pages
        for page_num in range(old_page_count):
            page_job = PageJob(
                session_id=session.id,
                drawing_id=old_drawing.id,
                page_number=page_num,
                job_type='ocr',
                status='pending'
            )
            page_jobs.append(page_job)
            db.add(page_job)
        
        # OCR jobs for new drawing pages
        for page_num in range(new_page_count):
            page_job = PageJob(
                session_id=session.id,
                drawing_id=new_drawing.id,
                page_number=page_num,
                job_type='ocr',
                status='pending'
            )
            page_jobs.append(page_job)
            db.add(page_job)
        
        db.commit()
        
        # Publish OCR messages to Pub/Sub (one per page)
        for page_job in page_jobs:
            message_data = {
                'page_job_id': page_job.id,
                'session_id': session.id,
                'drawing_id': page_job.drawing_id,
                'page_number': page_job.page_number,
                'storage_path': old_drawing.storage_path if page_job.drawing_id == old_drawing.id else new_drawing.storage_path
            }
            
            future = publisher.publish(
                ocr_topic_path,
                json.dumps(message_data).encode('utf-8'),
                session_id=session.id,
                job_id=page_job.id
            )
            
            print(f"Published OCR message for page {page_job.page_number}: {future.result()}")
        
        return jsonify({
            'session_id': session.id,
            'status': 'processing',
            'total_pages_old': old_page_count,
            'total_pages_new': new_page_count,
            'total_ocr_jobs': len(page_jobs),
            'websocket_room': f"session_{session.id}"
        }), 201

# ============================================================================
# COMPARISON STATUS & RESULTS
# ============================================================================

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """
    Get session status with page-level progress
    
    Response:
    {
        "session_id": "uuid",
        "status": "processing",
        "progress": {
            "ocr": {
                "total": 10,
                "completed": 7,
                "failed": 0,
                "percentage": 70
            },
            "diff": {
                "total": 5,
                "completed": 3,
                "failed": 0,
                "percentage": 60
            },
            "summary": {
                "total": 5,
                "completed": 1,
                "failed": 0,
                "percentage": 20
            }
        },
        "comparisons": [
            {
                "drawing_name": "A-101",
                "status": "completed",
                "overlay_url": "...",
                "summary": "..."
            }
        ]
    }
    """
    with get_db_session() as db:
        session = db.query(Session).get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get page job statistics
        ocr_jobs = db.query(PageJob).filter_by(
            session_id=session_id,
            job_type='ocr'
        ).all()
        
        ocr_total = len(ocr_jobs)
        ocr_completed = sum(1 for j in ocr_jobs if j.status == 'completed')
        ocr_failed = sum(1 for j in ocr_jobs if j.status == 'failed')
        
        # Get comparisons (page pairs)
        comparisons = db.query(Comparison).filter_by(
            session_id=session_id
        ).all()
        
        diff_total = len(comparisons)
        diff_completed = sum(1 for c in comparisons if c.status == 'completed')
        
        # Get summaries
        summaries = db.query(ChangeSummary).join(Comparison).filter(
            Comparison.session_id == session_id
        ).all()
        
        summary_total = len(summaries)
        summary_completed = sum(1 for s in summaries if s.status == 'completed')
        
        # Build comparison results
        comparison_results = []
        for comparison in comparisons:
            summary = db.query(ChangeSummary).filter_by(
                comparison_id=comparison.id
            ).first()
            
            comparison_results.append({
                'drawing_name': comparison.drawing_name,
                'status': comparison.status,
                'overlay_url': storage_service.get_signed_url(comparison.overlay_path) if comparison.overlay_path else None,
                'alignment_score': comparison.alignment_score,
                'summary': summary.summary_text if summary else None,
                'changes_count': len(summary.changes_found) if summary and summary.changes_found else 0
            })
        
        return jsonify({
            'session_id': session_id,
            'status': session.status,
            'progress': {
                'ocr': {
                    'total': ocr_total,
                    'completed': ocr_completed,
                    'failed': ocr_failed,
                    'percentage': (ocr_completed / ocr_total * 100) if ocr_total > 0 else 0
                },
                'diff': {
                    'total': diff_total,
                    'completed': diff_completed,
                    'failed': 0,
                    'percentage': (diff_completed / diff_total * 100) if diff_total > 0 else 0
                },
                'summary': {
                    'total': summary_total,
                    'completed': summary_completed,
                    'failed': 0,
                    'percentage': (summary_completed / summary_total * 100) if summary_total > 0 else 0
                }
            },
            'comparisons': comparison_results
        })

# ============================================================================
# WEBSOCKET HANDLERS (Real-Time Updates)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Client connected to WebSocket"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to BuildTrace server'})

@socketio.on('join_session')
def handle_join_session(data):
    """Join session room for real-time updates"""
    session_id = data.get('session_id')
    room = f"session_{session_id}"
    join_room(room)
    print(f"Client {request.sid} joined room {room}")
    emit('joined_session', {'session_id': session_id, 'room': room})

@socketio.on('leave_session')
def handle_leave_session(data):
    """Leave session room"""
    session_id = data.get('session_id')
    room = f"session_{session_id}"
    leave_room(room)
    print(f"Client {request.sid} left room {room}")

def broadcast_progress(session_id, event_type, data):
    """
    Broadcast progress update to all clients in session room
    
    Event types:
    - page_ocr_complete: {drawing_type, page_number, drawing_name}
    - pair_diff_complete: {drawing_name, overlay_url}
    - summary_complete: {drawing_name, summary}
    - session_complete: {}
    """
    room = f"session_{session_id}"
    socketio.emit(event_type, data, room=room)
    print(f"Broadcast {event_type} to room {room}: {data}")

# ============================================================================
# MANUAL OVERLAY EDITING
# ============================================================================

@app.route('/api/comparisons/<comparison_id>/overlay', methods=['PATCH'])
def update_manual_overlay(comparison_id):
    """Save manual overlay edits"""
    user = get_current_user()
    data = request.json
    
    with get_db_session() as db:
        comparison = db.query(Comparison).get(comparison_id)
        
        if not comparison:
            return jsonify({'error': 'Comparison not found'}), 404
        
        # Create manual overlay record
        manual_overlay = ManualOverlay(
            comparison_id=comparison_id,
            overlay_data=data['regions'],  # Array of edited regions
            created_by=user.id,
            is_active=True
        )
        db.add(manual_overlay)
        
        # Save overlay JSON to GCS
        overlay_ref = f"manual_overlays/{comparison_id}/{manual_overlay.id}.json"
        storage_service.upload_json(data['regions'], overlay_ref)
        manual_overlay.overlay_ref = overlay_ref
        
        db.commit()
        
        return jsonify({
            'manual_overlay_id': manual_overlay.id,
            'overlay_ref': overlay_ref,
            'created_at': manual_overlay.created_at.isoformat()
        })

@app.route('/api/comparisons/<comparison_id>/regenerate', methods=['POST'])
def regenerate_summary(comparison_id):
    """Regenerate summary with manual overlay"""
    data = request.json
    manual_overlay_id = data.get('manual_overlay_id')
    
    with get_db_session() as db:
        comparison = db.query(Comparison).get(comparison_id)
        
        if not comparison:
            return jsonify({'error': 'Comparison not found'}), 404
        
        # Publish summary message with manual overlay reference
        message_data = {
            'comparison_id': comparison_id,
            'manual_overlay_id': manual_overlay_id,
            'overlay_path': comparison.overlay_path,
            'regenerate': True
        }
        
        future = publisher.publish(
            summary_topic_path,
            json.dumps(message_data).encode('utf-8'),
            comparison_id=comparison_id
        )
        
        return jsonify({
            'message': 'Summary regeneration started',
            'job_id': future.result()
        })

# ============================================================================
# HEALTH & MONITORING
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'api'}), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check (DB connection)"""
    try:
        with get_db_session() as db:
            db.execute('SELECT 1')
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    socketio.run(
        app,
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
```

### 3.2 OCR Worker Service

**File**: `ocr_worker_service.py`

```python
from flask import Flask
from google.cloud import pubsub_v1, storage
import json
import tempfile
import PyMuPDF as fitz
from PIL import Image
import io

# Import existing modules
from config import config
from extract_drawing import extract_drawing_name_from_page
from gcp.storage import storage_service
from gcp.database import get_db_session
from gcp.database.models import PageJob, PageResult, Drawing

app = Flask(__name__)

# Initialize Pub/Sub subscriber
subscriber = pubsub_v1.SubscriberClient()
project_id = config.GCP_PROJECT_ID
subscription_path = subscriber.subscription_path(project_id, 'ocr-worker-sub')

# Initialize Pub/Sub publisher (for completion events)
publisher = pubsub_v1.PublisherClient()

def process_ocr_message(message):
    """
    Process single page OCR job
    
    Message format:
    {
        "page_job_id": "uuid",
        "session_id": "uuid",
        "drawing_id": "uuid",
        "page_number": 0,
        "storage_path": "gs://bucket/path/to/file.pdf"
    }
    """
    try:
        data = json.loads(message.data.decode('utf-8'))
        
        page_job_id = data['page_job_id']
        session_id = data['session_id']
        drawing_id = data['drawing_id']
        page_number = data['page_number']
        storage_path = data['storage_path']
        
        print(f"Processing OCR for page {page_number} of drawing {drawing_id}")
        
        with get_db_session() as db:
            # Update job status
            page_job = db.query(PageJob).get(page_job_id)
            page_job.status = 'in_progress'
            page_job.started_at = datetime.utcnow()
            db.commit()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download PDF
                pdf_path = f"{temp_dir}/input.pdf"
                storage_service.download_file(storage_path, pdf_path)
                
                # Open PDF and extract specific page
                doc = fitz.open(pdf_path)
                page = doc[page_number]
                
                # Extract drawing name (reuse existing logic)
                drawing_name = extract_drawing_name_from_page(page)
                
                # Convert page to PNG
                pix = page.get_pixmap(dpi=300)
                png_data = pix.tobytes("png")
                
                # Upload PNG to GCS
                png_path = f"processed/{drawing_id}/page_{page_number}.png"
                storage_service.upload_bytes(png_data, png_path)
                
                # Create page result
                page_result = PageResult(
                    page_job_id=page_job_id,
                    session_id=session_id,
                    drawing_id=drawing_id,
                    page_number=page_number,
                    drawing_name=drawing_name,
                    png_path=png_path,
                    status='completed'
                )
                db.add(page_result)
                
                # Update drawing record with first page's name
                if page_number == 0:
                    drawing = db.query(Drawing).get(drawing_id)
                    drawing.drawing_name = drawing_name
                
                # Update job status
                page_job.status = 'completed'
                page_job.completed_at = datetime.utcnow()
                
                db.commit()
                
                doc.close()
                
                print(f"Completed OCR for page {page_number}: {drawing_name}")
                
                # Publish completion event (for orchestrator)
                completion_topic = publisher.topic_path(project_id, 'ocr-completions-topic')
                completion_data = {
                    'page_job_id': page_job_id,
                    'session_id': session_id,
                    'drawing_id': drawing_id,
                    'page_number': page_number,
                    'drawing_name': drawing_name,
                    'png_path': png_path
                }
                publisher.publish(
                    completion_topic,
                    json.dumps(completion_data).encode('utf-8')
                )
                
                # Acknowledge message
                message.ack()
                
    except Exception as e:
        print(f"Error processing OCR message: {e}")
        
        # Update job as failed
        try:
            with get_db_session() as db:
                page_job = db.query(PageJob).get(page_job_id)
                page_job.status = 'failed'
                page_job.error_message = str(e)
                page_job.completed_at = datetime.utcnow()
                db.commit()
        except:
            pass
        
        # Nack message for retry
        message.nack()

def start_subscriber():
    """Start Pub/Sub subscriber"""
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=process_ocr_message
    )
    
    print(f"Listening for OCR messages on {subscription_path}")
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        streaming_pull_future.result()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'ocr-worker'}), 200

if __name__ == '__main__':
    # Start subscriber in background thread
    import threading
    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()
    
    # Run Flask for health checks
    app.run(host='0.0.0.0', port=8081)
```

### 3.3 Diff Worker Service

**File**: `diff_worker_service.py`

```python
from flask import Flask
from google.cloud import pubsub_v1
import json
import tempfile
import cv2
import numpy as np

# Import existing modules
from config import config
from align_drawings import AlignDrawings
from gcp.storage import storage_service
from gcp.database import get_db_session
from gcp.database.models import Comparison, PageResult

app = Flask(__name__)

# Initialize Pub/Sub
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()
project_id = config.GCP_PROJECT_ID
subscription_path = subscriber.subscription_path(project_id, 'diff-worker-sub')

# Initialize aligner (reuse existing SIFT logic)
aligner = AlignDrawings(debug=False)

def process_diff_message(message):
    """
    Process single page pair diff job
    
    Message format:
    {
        "session_id": "uuid",
        "old_page_result_id": "uuid",
        "new_page_result_id": "uuid",
        "drawing_name": "A-101"
    }
    """
    try:
        data = json.loads(message.data.decode('utf-8'))
        
        session_id = data['session_id']
        old_page_result_id = data['old_page_result_id']
        new_page_result_id = data['new_page_result_id']
        drawing_name = data['drawing_name']
        
        print(f"Processing diff for {drawing_name}")
        
        with get_db_session() as db:
            # Get page results
            old_page = db.query(PageResult).get(old_page_result_id)
            new_page = db.query(PageResult).get(new_page_result_id)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download PNGs
                old_png_path = f"{temp_dir}/old.png"
                new_png_path = f"{temp_dir}/new.png"
                
                storage_service.download_file(old_page.png_path, old_png_path)
                storage_service.download_file(new_page.png_path, new_png_path)
                
                # Load images
                old_img = cv2.imread(old_png_path)
                new_img = cv2.imread(new_png_path)
                
                # Align drawings (reuse existing SIFT logic)
                aligned_old = aligner(old_img, new_img)
                alignment_score = aligner.last_alignment_score if hasattr(aligner, 'last_alignment_score') else 0.8
                
                # Create overlay (red=old, green=new)
                overlay = np.zeros_like(new_img)
                overlay[:, :, 2] = cv2.cvtColor(aligned_old, cv2.COLOR_BGR2GRAY)  # Red channel
                overlay[:, :, 1] = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)      # Green channel
                
                # Save overlay
                overlay_path_local = f"{temp_dir}/overlay.png"
                cv2.imwrite(overlay_path_local, overlay)
                
                # Upload to GCS
                overlay_gcs_path = f"overlays/{session_id}/{drawing_name}_overlay.png"
                storage_service.upload_file(overlay_path_local, overlay_gcs_path)
                
                # Create comparison record
                comparison = Comparison(
                    session_id=session_id,
                    old_page_result_id=old_page_result_id,
                    new_page_result_id=new_page_result_id,
                    drawing_name=drawing_name,
                    overlay_path=overlay_gcs_path,
                    old_image_path=old_page.png_path,
                    new_image_path=new_page.png_path,
                    alignment_score=alignment_score,
                    status='completed'
                )
                db.add(comparison)
                db.commit()
                
                print(f"Completed diff for {drawing_name}, comparison_id: {comparison.id}")
                
                # Publish completion event
                completion_topic = publisher.topic_path(project_id, 'diff-completions-topic')
                completion_data = {
                    'comparison_id': comparison.id,
                    'session_id': session_id,
                    'drawing_name': drawing_name,
                    'overlay_path': overlay_gcs_path
                }
                publisher.publish(
                    completion_topic,
                    json.dumps(completion_data).encode('utf-8')
                )
                
                # Also publish to summary topic
                summary_topic = publisher.topic_path(project_id, 'summary-overlays-topic')
                summary_data = {
                    'comparison_id': comparison.id,
                    'overlay_path': overlay_gcs_path,
                    'drawing_name': drawing_name
                }
                publisher.publish(
                    summary_topic,
                    json.dumps(summary_data).encode('utf-8')
                )
                
                message.ack()
                
    except Exception as e:
        print(f"Error processing diff message: {e}")
        message.nack()

def start_subscriber():
    """Start Pub/Sub subscriber"""
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=process_diff_message
    )
    
    print(f"Listening for diff messages on {subscription_path}")
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        streaming_pull_future.result()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'diff-worker'}), 200

if __name__ == '__main__':
    import threading
    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()
    
    app.run(host='0.0.0.0', port=8082)
```

### 3.4 Summary Worker Service

**File**: `summary_worker_service.py`

```python
from flask import Flask
from google.cloud import pubsub_v1
import json
import tempfile

# Import existing modules
from config import config
from openai_change_analyzer import OpenAIChangeAnalyzer
from gcp.storage import storage_service
from gcp.database import get_db_session
from gcp.database.models import ChangeSummary, Comparison, ManualOverlay

app = Flask(__name__)

# Initialize Pub/Sub
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()
project_id = config.GCP_PROJECT_ID
subscription_path = subscriber.subscription_path(project_id, 'summary-worker-sub')

# Initialize analyzer (reuse existing logic)
analyzer = OpenAIChangeAnalyzer()

def process_summary_message(message):
    """
    Process single overlay analysis job
    
    Message format:
    {
        "comparison_id": "uuid",
        "overlay_path": "gs://...",
        "drawing_name": "A-101",
        "manual_overlay_id": "uuid" (optional)
    }
    """
    try:
        data = json.loads(message.data.decode('utf-8'))
        
        comparison_id = data['comparison_id']
        overlay_path = data['overlay_path']
        drawing_name = data['drawing_name']
        manual_overlay_id = data.get('manual_overlay_id')
        
        print(f"Processing summary for {drawing_name}")
        
        with get_db_session() as db:
            comparison = db.query(Comparison).get(comparison_id)
            
            # Determine which overlay to use
            if manual_overlay_id:
                manual_overlay = db.query(ManualOverlay).get(manual_overlay_id)
                overlay_path = manual_overlay.overlay_ref
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download overlay
                overlay_local = f"{temp_dir}/overlay.png"
                storage_service.download_file(overlay_path, overlay_local)
                
                # Analyze using OpenAI (reuse existing logic)
                result = analyzer.analyze_overlay_image(overlay_local)
                
                # Create summary record
                summary = ChangeSummary(
                    comparison_id=comparison_id,
                    manual_overlay_id=manual_overlay_id,
                    summary_text=result.analysis_summary,
                    changes_found=result.changes_found,
                    critical_change=result.critical_change,
                    recommendations=result.recommendations,
                    source='human_corrected' if manual_overlay_id else 'machine',
                    model_version='gpt-4o',
                    status='completed'
                )
                db.add(summary)
                db.commit()
                
                print(f"Completed summary for {drawing_name}")
                
                # Publish completion event
                completion_topic = publisher.topic_path(project_id, 'summary-completions-topic')
                completion_data = {
                    'summary_id': summary.id,
                    'comparison_id': comparison_id,
                    'drawing_name': drawing_name
                }
                publisher.publish(
                    completion_topic,
                    json.dumps(completion_data).encode('utf-8')
                )
                
                message.ack()
                
    except Exception as e:
        print(f"Error processing summary message: {e}")
        message.nack()

def start_subscriber():
    """Start Pub/Sub subscriber"""
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=process_summary_message
    )
    
    print(f"Listening for summary messages on {subscription_path}")
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        streaming_pull_future.result()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'summary-worker'}), 200

if __name__ == '__main__':
    import threading
    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()
    
    app.run(host='0.0.0.0', port=8083)
```

---

## 4. Database Schema (Enhanced for Page-Level Processing)

```sql
-- ============================================================================
-- USERS & AUTHENTICATION
-- ============================================================================

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    role VARCHAR(100),
    password_hash VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- PROJECT MANAGEMENT
-- ============================================================================

CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_number VARCHAR(100),
    client_name VARCHAR(255),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE project_users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    invited_at TIMESTAMP DEFAULT NOW(),
    invited_by VARCHAR(36) REFERENCES users(id),
    UNIQUE (project_id, user_id)
);

CREATE TABLE drawing_versions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE,
    drawing_name VARCHAR(100) NOT NULL,
    version_number INTEGER NOT NULL,
    version_label VARCHAR(50),
    file_name VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    file_size INTEGER,
    upload_date TIMESTAMP DEFAULT NOW(),
    uploaded_by VARCHAR(36) REFERENCES users(id),
    comments TEXT,
    UNIQUE (project_id, drawing_name, version_number)
);

-- ============================================================================
-- PROCESSING SESSIONS
-- ============================================================================

CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(36) REFERENCES users(id),
    project_id VARCHAR(36) REFERENCES projects(id),
    session_type VARCHAR(50) DEFAULT 'comparison',
    status VARCHAR(50) DEFAULT 'processing',
    total_time FLOAT,
    session_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE drawings (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id),
    drawing_type VARCHAR(20) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    drawing_name VARCHAR(100),
    drawing_metadata JSONB,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- PAGE-LEVEL PROCESSING (NEW!)
-- ============================================================================

CREATE TABLE page_jobs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    drawing_id VARCHAR(36) REFERENCES drawings(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE page_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    page_job_id VARCHAR(36) REFERENCES page_jobs(id) ON DELETE CASCADE,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    drawing_id VARCHAR(36) REFERENCES drawings(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    drawing_name VARCHAR(100),
    png_path TEXT,
    ocr_data JSONB,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- COMPARISONS (Page-Pair Level)
-- ============================================================================

CREATE TABLE comparisons (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    old_page_result_id VARCHAR(36) REFERENCES page_results(id),
    new_page_result_id VARCHAR(36) REFERENCES page_results(id),
    drawing_name VARCHAR(100) NOT NULL,
    overlay_path TEXT,
    old_image_path TEXT,
    new_image_path TEXT,
    alignment_score FLOAT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (session_id, drawing_name)
);

-- ============================================================================
-- MANUAL OVERLAYS & SUMMARIES
-- ============================================================================

CREATE TABLE manual_overlays (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    comparison_id VARCHAR(36) REFERENCES comparisons(id) ON DELETE CASCADE,
    overlay_ref TEXT NOT NULL,
    overlay_data JSONB,
    created_by VARCHAR(36) REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE change_summaries (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    comparison_id VARCHAR(36) REFERENCES comparisons(id) ON DELETE CASCADE,
    manual_overlay_id VARCHAR(36) REFERENCES manual_overlays(id),
    summary_text TEXT,
    changes_found JSONB,
    critical_change TEXT,
    recommendations JSONB,
    source VARCHAR(20) NOT NULL,
    model_version VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- CHAT (Keep existing)
-- ============================================================================

CREATE TABLE chat_conversations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(36) REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    message_metadata JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_project_id ON sessions(project_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_drawings_session_id ON drawings(session_id);
CREATE INDEX idx_page_jobs_session_id ON page_jobs(session_id);
CREATE INDEX idx_page_jobs_status ON page_jobs(status);
CREATE INDEX idx_page_results_session_id ON page_results(session_id);
CREATE INDEX idx_comparisons_session_id ON comparisons(session_id);
CREATE INDEX idx_comparisons_status ON comparisons(status);
CREATE INDEX idx_change_summaries_comparison_id ON change_summaries(comparison_id);
```

---

## 5. Orchestrator Service

**File**: `orchestrator_service.py`

```python
from flask import Flask
from google.cloud import pubsub_v1
import json
import time
from datetime import datetime

# Import existing modules
from config import config
from gcp.database import get_db_session
from gcp.database.models import (
    Session, PageJob, PageResult, Comparison, ChangeSummary
)
from api_service import broadcast_progress

app = Flask(__name__)

# Initialize Pub/Sub
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()
project_id = config.GCP_PROJECT_ID

# Subscribe to completion topics
ocr_completion_sub = subscriber.subscription_path(project_id, 'ocr-completions-sub')
diff_completion_sub = subscriber.subscription_path(project_id, 'diff-completions-sub')
summary_completion_sub = subscriber.subscription_path(project_id, 'summary-completions-sub')

def handle_ocr_completion(message):
    """
    Handle OCR page completion
    
    1. Check if all OCR pages for session are complete
    2. If yes, match drawings and publish diff messages
    """
    try:
        data = json.loads(message.data.decode('utf-8'))
        
        session_id = data['session_id']
        drawing_name = data['drawing_name']
        page_number = data['page_number']
        
        print(f"OCR completed: session={session_id}, page={page_number}, drawing={drawing_name}")
        
        # Broadcast progress
        broadcast_progress(session_id, 'page_ocr_complete', {
            'page_number': page_number,
            'drawing_name': drawing_name
        })
        
        with get_db_session() as db:
            # Check if all OCR jobs for session are complete
            ocr_jobs = db.query(PageJob).filter_by(
                session_id=session_id,
                job_type='ocr'
            ).all()
            
            all_complete = all(job.status == 'completed' for job in ocr_jobs)
            
            if all_complete:
                print(f"All OCR jobs complete for session {session_id}, starting diff matching")
                
                # Get all page results
                page_results = db.query(PageResult).filter_by(
                    session_id=session_id
                ).all()
                
                # Group by drawing name
                old_pages = {}
                new_pages = {}
                
                for result in page_results:
                    drawing = db.query(Drawing).get(result.drawing_id)
                    
                    if result.drawing_name:
                        if drawing.drawing_type == 'old':
                            old_pages[result.drawing_name] = result
                        else:
                            new_pages[result.drawing_name] = result
                
                # Match drawings
                matched_drawings = set(old_pages.keys()).intersection(set(new_pages.keys()))
                
                print(f"Found {len(matched_drawings)} matched drawings: {matched_drawings}")
                
                # Publish diff messages for each match
                diff_topic = publisher.topic_path(project_id, 'diff-pairs-topic')
                
                for drawing_name in matched_drawings:
                    diff_message = {
                        'session_id': session_id,
                        'old_page_result_id': old_pages[drawing_name].id,
                        'new_page_result_id': new_pages[drawing_name].id,
                        'drawing_name': drawing_name
                    }
                    
                    publisher.publish(
                        diff_topic,
                        json.dumps(diff_message).encode('utf-8')
                    )
                    
                    print(f"Published diff message for {drawing_name}")
                
                # Broadcast OCR stage complete
                broadcast_progress(session_id, 'ocr_stage_complete', {
                    'total_pages': len(page_results),
                    'matched_drawings': len(matched_drawings)
                })
        
        message.ack()
        
    except Exception as e:
        print(f"Error handling OCR completion: {e}")
        message.nack()

def handle_diff_completion(message):
    """
    Handle diff completion
    
    Broadcast result so frontend can populate carousel
    """
    try:
        data = json.loads(message.data.decode('utf-8'))
        
        comparison_id = data['comparison_id']
        session_id = data['session_id']
        drawing_name = data['drawing_name']
        overlay_path = data['overlay_path']
        
        print(f"Diff completed: {drawing_name}")
        
        with get_db_session() as db:
            comparison = db.query(Comparison).get(comparison_id)
            
            # Generate signed URL for overlay
            from gcp.storage import storage_service
            overlay_url = storage_service.get_signed_url(overlay_path)
            
            # Broadcast progress (frontend populates carousel!)
            broadcast_progress(session_id, 'pair_diff_complete', {
                'drawing_name': drawing_name,
                'comparison_id': comparison_id,
                'overlay_url': overlay_url,
                'alignment_score': comparison.alignment_score
            })
        
        message.ack()
        
    except Exception as e:
        print(f"Error handling diff completion: {e}")
        message.nack()

def handle_summary_completion(message):
    """
    Handle summary completion
    
    Broadcast result so frontend can show summary in carousel
    """
    try:
        data = json.loads(message.data.decode('utf-8'))
        
        summary_id = data['summary_id']
        comparison_id = data['comparison_id']
        drawing_name = data['drawing_name']
        
        print(f"Summary completed: {drawing_name}")
        
        with get_db_session() as db:
            summary = db.query(ChangeSummary).get(summary_id)
            comparison = db.query(Comparison).get(comparison_id)
            
            # Broadcast progress
            broadcast_progress(comparison.session_id, 'summary_complete', {
                'drawing_name': drawing_name,
                'comparison_id': comparison_id,
                'summary': summary.summary_text,
                'changes_count': len(summary.changes_found) if summary.changes_found else 0,
                'critical_change': summary.critical_change
            })
            
            # Check if all summaries for session are complete
            session = db.query(Session).get(comparison.session_id)
            all_comparisons = db.query(Comparison).filter_by(
                session_id=session.id
            ).all()
            
            all_summaries_complete = all(
                db.query(ChangeSummary).filter_by(comparison_id=c.id).first() is not None
                for c in all_comparisons
            )
            
            if all_summaries_complete:
                print(f"All summaries complete for session {session.id}")
                
                # Update session status
                session.status = 'completed'
                db.commit()
                
                # Broadcast session complete
                broadcast_progress(session.id, 'session_complete', {
                    'message': 'All comparisons complete'
                })
        
        message.ack()
        
    except Exception as e:
        print(f"Error handling summary completion: {e}")
        message.nack()

def start_orchestrator():
    """Start all completion listeners"""
    
    # OCR completions
    ocr_future = subscriber.subscribe(ocr_completion_sub, callback=handle_ocr_completion)
    print(f"Listening for OCR completions on {ocr_completion_sub}")
    
    # Diff completions
    diff_future = subscriber.subscribe(diff_completion_sub, callback=handle_diff_completion)
    print(f"Listening for diff completions on {diff_completion_sub}")
    
    # Summary completions
    summary_future = subscriber.subscribe(summary_completion_sub, callback=handle_summary_completion)
    print(f"Listening for summary completions on {summary_completion_sub}")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ocr_future.cancel()
        diff_future.cancel()
        summary_future.cancel()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'orchestrator'}), 200

if __name__ == '__main__':
    import threading
    orchestrator_thread = threading.Thread(target=start_orchestrator, daemon=True)
    orchestrator_thread.start()
    
    app.run(host='0.0.0.0', port=8084)
```

---

**END OF PART 1**

This completes Part 1 covering:
- ✅ Executive Summary & Goals
- ✅ Architecture Overview (Page-Level Pub/Sub)
- ✅ Flask API Service (with Flask-SocketIO)
- ✅ OCR, Diff, Summary Worker Services
- ✅ Enhanced Database Schema (page-level tables)
- ✅ Orchestrator Service (completion handlers)

**Part 2 will cover:**
- Frontend Architecture (based on screenshots)
- GKE Deployment (Kubernetes manifests)
- Implementation Roadmap
- Monitoring & Testing
- Cost Optimization

