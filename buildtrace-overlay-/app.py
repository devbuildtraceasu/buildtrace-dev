#!/usr/bin/env python3
"""
BuildTrace AI Web Application - Unified Version
Supports both local and cloud deployments through environment configuration
"""

import os
import json
import uuid
import logging
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

# Import configuration and services
from config import config
from gcp.storage import storage_service
from gcp.database import get_db_session, init_db
from gcp.database.models import Session, Drawing, Comparison, AnalysisResult

# Import existing modules
from complete_drawing_pipeline import complete_drawing_pipeline
from chunked_processor import process_documents as chunked_process_documents
from chatbot_service import ConstructionChatBot, ChatMessage
from openai_change_analyzer import ChangeAnalysisResult
from session_summary_api import session_summary_bp

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL if hasattr(config, 'LOG_LEVEL') else 'INFO'))
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Simple in-memory cache for recent sessions
class SimpleCache:
    def __init__(self, ttl=30):  # 30 seconds TTL by default
        self.cache = {}
        self.ttl = ttl

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

    def clear(self, key=None):
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()

# Initialize cache for recent sessions (30 second TTL)
recent_sessions_cache = SimpleCache(ttl=30)

# Initialize services based on configuration
logger.info(f"Initializing BuildTrace in {config.ENVIRONMENT} mode")
logger.info(f"Features: DB={config.USE_DATABASE}, GCS={config.USE_GCS}, Async={config.USE_ASYNC_PROCESSING}")

# Services are directly imported and ready to use
# storage_service is imported from gcp.storage
# data_service is replaced by get_db_session from gcp.database


def serialize_results_for_json(results):
    """Convert results containing ChangeAnalysisResult objects to JSON-serializable format with restructured analysis data"""
    if not isinstance(results, dict):
        return results

    serialized = {}
    for key, value in results.items():
        if isinstance(value, list):
            # Handle lists that might contain ChangeAnalysisResult objects or analysis data
            processed_list = []
            for item in value:
                if isinstance(item, ChangeAnalysisResult):
                    processed_list.append(item.to_dict())
                elif isinstance(item, dict) and 'analysis_summary' in item:
                    # This is analysis data that needs restructuring
                    processed_list.append(restructure_analysis_data(item))
                else:
                    processed_list.append(serialize_results_for_json(item) if isinstance(item, dict) else item)
            serialized[key] = processed_list
        elif isinstance(value, dict):
            # Check if this is analysis data that needs restructuring
            if 'analysis_summary' in value and 'changes_found' in value:
                serialized[key] = restructure_analysis_data(value)
            else:
                # Recursively handle nested dictionaries
                serialized[key] = serialize_results_for_json(value)
        elif isinstance(value, ChangeAnalysisResult):
            # Convert ChangeAnalysisResult to dictionary
            serialized[key] = value.to_dict()
        else:
            serialized[key] = value

    return serialized

# Create necessary directories for local mode
if not config.USE_GCS:
    for folder in [config.LOCAL_UPLOAD_PATH, config.LOCAL_RESULTS_PATH, config.LOCAL_TEMP_PATH]:
        os.makedirs(folder, exist_ok=True)

if not config.USE_DATABASE:
    os.makedirs(config.get_data_config()['data_dir'], exist_ok=True)

# Initialize chatbot
chatbot = ConstructionChatBot()

# In-memory storage for local mode
if not config.USE_DATABASE:
    conversation_histories = {}

# Database initialization for cloud mode
if config.USE_DATABASE:
    try:
        from gcp.database import get_db_session, init_db
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if config.IS_PRODUCTION:
            logger.warning("Database unavailable in production, uploads will use local fallback mode")
            # Don't raise exception, let the app continue with fallback mode

# Register blueprints
app.register_blueprint(session_summary_bp)

def restructure_analysis_data(analysis_data):
    """Restructure analysis data for better frontend consumption"""
    try:
        # Extract the actual critical change content from analysis_summary
        critical_change_content = ""
        summary_text = analysis_data.get('analysis_summary', '')
        
        if '### 1. Most Critical Change' in summary_text:
            # Extract the critical change description
            lines = summary_text.split('\n')
            in_critical_section = False
            for line in lines:
                if '### 1. Most Critical Change' in line:
                    in_critical_section = True
                    continue
                elif in_critical_section and line.strip().startswith('###'):
                    break
                elif in_critical_section and line.strip():
                    critical_change_content = line.strip()
                    break
        
        # Parse changes_found into structured format
        structured_changes = []
        changes_found = analysis_data.get('changes_found', [])
        
        for change in changes_found:
            if isinstance(change, str) and not change.startswith('- **'):
                # This is a structured change (e.g., "1. **Roof Structure** + **Addition** + **Extended roof structure** + **North Elevation**")
                if '**' in change and ' + ' in change:
                    parts = change.split(' + ')
                    if len(parts) >= 4:
                        structured_changes.append({
                            'component': parts[0].replace('**', '').strip(),
                            'change_type': parts[1].replace('**', '').strip(),
                            'description': parts[2].replace('**', '').strip(),
                            'location': parts[3].replace('**', '').strip()
                        })
        
        # Extract impact analysis (the bullet points with impact details)
        impact_analysis = []
        for change in changes_found:
            if isinstance(change, str) and change.startswith('- **') and '**:' in change:
                # This is an impact analysis line
                impact_analysis.append(change.replace('- **', '').replace('**:', ':').strip())
        
        # Extract recommendations from analysis_summary
        recommendations = []
        if '### 4. Recommendations' in summary_text:
            rec_section = summary_text.split('### 4. Recommendations')[1]
            rec_lines = rec_section.split('\n')
            for line in rec_lines:
                line = line.strip()
                if line.startswith('- **') and '**:' in line:
                    rec = line.replace('- **', '').replace('**:', ':').strip()
                    recommendations.append(rec)
        
        # Create construction impact summary
        construction_impact = ""
        if '### 3. Construction Impact' in summary_text:
            impact_start = summary_text.find('### 3. Construction Impact')
            if impact_start != -1:
                impact_section = summary_text[impact_start + len('### 3. Construction Impact'):]
                # Get first few sentences
                sentences = impact_section.split('. ')
                if sentences and len(sentences[0]) > 20:
                    construction_impact = sentences[0].strip() + '.'
                else:
                    construction_impact = "Multiple structural and system changes affecting cost and timeline"
        
        return {
            'drawing_name': analysis_data.get('drawing_name', ''),
            'success': analysis_data.get('success', True),
            'critical_change': {
                'title': 'Most Critical Change',
                'content': critical_change_content or "Significant structural changes detected",
                'component': structured_changes[0]['component'] if structured_changes else 'Unknown',
                'impact': construction_impact
            },
            'changes_breakdown': structured_changes,
            'impact_analysis': impact_analysis,
            'recommendations': recommendations[:4],  # Limit to top 4
            'construction_impact': construction_impact,
            'analysis_timestamp': analysis_data.get('analysis_timestamp', ''),
            'overlay_folder': analysis_data.get('overlay_folder', '')
        }
        
    except Exception as e:
        logger.error(f"Error restructuring analysis data: {e}")
        # Return original data if restructuring fails
        return analysis_data

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main upload interface"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for database connectivity"""
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'storage': 'unknown',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Check database connectivity
    if config.USE_DATABASE:
        try:
            with get_db_session() as db:
                # Simple query to test connection
                db.execute("SELECT 1")
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
    else:
        health_status['database'] = 'disabled'
    
    # Check storage connectivity
    try:
        # Test storage service
        test_path = f"health-check-{datetime.now().timestamp()}"
        storage_service.upload_file(b"test", test_path)
        health_status['storage'] = 'connected'
    except Exception as e:
        health_status['storage'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    return jsonify(health_status)

@app.route('/api/upload-urls', methods=['POST'])
def get_upload_urls():
    """Generate signed URLs for direct Cloud Storage upload"""
    try:
        data = request.get_json()
        if not data or 'files' not in data:
            return jsonify({'error': 'Missing files data'}), 400

        files = data['files']
        if len(files) != 2:
            return jsonify({'error': 'Exactly 2 files required'}), 400

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Generate signed upload URLs for each file
        upload_urls = {}
        for file_info in files:
            if 'name' not in file_info or 'type' not in file_info:
                return jsonify({'error': 'File name and type required'}), 400

            filename = secure_filename(file_info['name'])
            file_type = file_info['type']  # 'old' or 'new'

            # Create storage path
            storage_path = f"sessions/{session_id}/{file_type}_{filename}"

            # Generate signed upload URL (valid for 1 hour)
            if config.USE_GCS and hasattr(storage_service, 'generate_signed_upload_url'):
                try:
                    signed_url = storage_service.generate_signed_upload_url(
                        storage_path,
                        content_type='application/pdf',
                        expiration_minutes=60
                    )
                    upload_urls[file_type] = {
                        'upload_url': signed_url,
                        'storage_path': storage_path,
                        'filename': filename
                    }
                except Exception as e:
                    logger.error(f"Failed to generate signed URL for {file_type}: {e}")
                    return jsonify({'error': f'Failed to generate upload URL for {file_type}'}), 500
            else:
                return jsonify({'error': 'Cloud Storage not available'}), 503

        # Store session metadata
        if config.USE_DATABASE:
            try:
                from gcp.database.models import Session
                with get_db_session() as db:
                    session = Session(
                        id=session_id,
                        status='uploading',
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(session)
                    db.commit()
                    logger.info(f"Created session {session_id} for direct upload")
            except Exception as e:
                logger.warning(f"Failed to create session in database: {e}")

        return jsonify({
            'session_id': session_id,
            'upload_urls': upload_urls
        })

    except Exception as e:
        logger.error(f"Error generating upload URLs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-uploaded-files', methods=['POST'])
def process_uploaded_files():
    """Process files that have been uploaded directly to Cloud Storage"""
    try:
        data = request.get_json()
        if not data or 'session_id' not in data or 'files' not in data:
            return jsonify({'error': 'Missing session_id or files data'}), 400

        session_id = data['session_id']
        files = data['files']

        if len(files) != 2:
            return jsonify({'error': 'Exactly 2 files required'}), 400

        # Validate that files exist in storage
        old_storage_path = None
        new_storage_path = None

        for file_type, file_info in files.items():
            if file_type not in ['old', 'new']:
                return jsonify({'error': f'Invalid file type: {file_type}'}), 400

            storage_path = file_info.get('storage_path')
            if not storage_path:
                return jsonify({'error': f'Missing storage_path for {file_type} file'}), 400

            # Check if file exists in storage
            if not storage_service.file_exists(storage_path):
                return jsonify({'error': f'File not found in storage: {storage_path}'}), 404

            if file_type == 'old':
                old_storage_path = storage_path
            else:
                new_storage_path = storage_path

        logger.info(f"Processing files from Cloud Storage for session {session_id}")
        logger.info(f"Old file: {old_storage_path}")
        logger.info(f"New file: {new_storage_path}")

        # Update session status to processing
        if config.USE_DATABASE:
            try:
                from gcp.database.models import Session
                with get_db_session() as db:
                    session = db.query(Session).filter(Session.id == session_id).first()
                    if session:
                        session.status = 'processing'
                        session.baseline_filename = files['old'].get('filename', 'old_file.pdf')
                        session.revised_filename = files['new'].get('filename', 'new_file.pdf')
                        db.commit()
                        logger.info(f"Updated session {session_id} status to processing")
            except Exception as e:
                logger.warning(f"Failed to update session in database: {e}")

        # Download files from storage to temporary locations for processing
        old_temp_path = None
        new_temp_path = None

        try:
            # Create temporary files
            old_temp_fd, old_temp_path = tempfile.mkstemp(suffix='.pdf', prefix='old_')
            new_temp_fd, new_temp_path = tempfile.mkstemp(suffix='.pdf', prefix='new_')

            # Close file descriptors since we'll use the paths directly
            os.close(old_temp_fd)
            os.close(new_temp_fd)

            # Download files from storage
            if not storage_service.download_to_filename(old_storage_path, old_temp_path):
                raise Exception(f"Failed to download old file from {old_storage_path}")

            if not storage_service.download_to_filename(new_storage_path, new_temp_path):
                raise Exception(f"Failed to download new file from {new_storage_path}")

            logger.info(f"Downloaded files to temporary locations: {old_temp_path}, {new_temp_path}")

            # Process the files using chunked_process_documents
            logger.info(f"Starting processing for session {session_id}")
            results = chunked_process_documents(old_temp_path, new_temp_path, session_id)

            if results:
                logger.info(f"Processing completed successfully for session {session_id}")

                # Update session status and results
                if config.USE_DATABASE:
                    try:
                        with get_db_session() as db:
                            session = db.query(Session).filter(Session.id == session_id).first()
                            if session:
                                session.status = 'completed'
                                session.changes_count = len(results.get('changes', []))
                                session.completed_at = datetime.now(timezone.utc)
                                db.commit()
                                logger.info(f"Updated session {session_id} status to completed")
                    except Exception as e:
                        logger.warning(f"Failed to update session completion in database: {e}")

                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'redirect_url': f'/results/{session_id}',
                    'message': 'Processing completed successfully'
                })
            else:
                raise Exception("Processing failed - no results returned")

        finally:
            # Clean up temporary files
            for temp_path in [old_temp_path, new_temp_path]:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                        logger.info(f"Cleaned up temporary file: {temp_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

    except Exception as e:
        logger.error(f"Error processing uploaded files: {e}")

        # Update session status to failed
        if config.USE_DATABASE:
            try:
                from gcp.database.models import Session
                with get_db_session() as db:
                    session = db.query(Session).filter(Session.id == session_id).first()
                    if session:
                        session.status = 'failed'
                        session.error_message = str(e)
                        db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update session status to failed: {db_error}")

        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-direct/<path:storage_path>', methods=['PUT'])
def upload_direct_to_storage(storage_path):
    """Handle direct file upload to Cloud Storage for large files"""
    try:
        # Get the file content from the request body
        file_content = request.get_data()

        if not file_content:
            return jsonify({'error': 'No file content provided'}), 400

        logger.info(f"Uploading file directly to storage: {storage_path}, size: {len(file_content)} bytes")

        # Upload to Cloud Storage
        try:
            import io
            file_stream = io.BytesIO(file_content)

            # Determine content type
            content_type = request.headers.get('Content-Type', 'application/pdf')

            # Upload to storage
            storage_path_result = storage_service.upload_file(
                file_stream,
                storage_path,
                content_type=content_type
            )

            logger.info(f"File uploaded successfully to: {storage_path_result}")

            return jsonify({
                'success': True,
                'storage_path': storage_path,
                'message': 'File uploaded successfully'
            })

        except Exception as upload_error:
            logger.error(f"Failed to upload file to storage: {upload_error}")
            return jsonify({'error': f'Storage upload failed: {str(upload_error)}'}), 500

    except Exception as e:
        logger.error(f"Error in direct upload: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads (legacy endpoint for smaller files)"""
    try:
        # Check if files are provided
        if 'old_file' not in request.files or 'new_file' not in request.files:
            return jsonify({'error': 'Both old and new files are required'}), 400

        old_file = request.files['old_file']
        new_file = request.files['new_file']

        # Check if files are selected
        if old_file.filename == '' or new_file.filename == '':
            return jsonify({'error': 'No files selected'}), 400

        # Check file types
        if not (allowed_file(old_file.filename) and allowed_file(new_file.filename)):
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(config.ALLOWED_EXTENSIONS)}'}), 400

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Save session data to database
        from gcp.database.models import Session
        session_data = Session(
            id=session_id,
            session_type='comparison',
            status='active',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Save to database if using database mode
        if config.USE_DATABASE:
            try:
                with get_db_session() as db:
                    db.add(session_data)
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to save session to database: {e}")
                # Fallback to local mode if database fails
                logger.warning("Database unavailable, falling back to local mode")
                try:
                    session_folder = os.path.join('uploads', session_id)
                    os.makedirs(session_folder, exist_ok=True)
                    
                    session_metadata = {
                        'id': session_id,
                        'session_type': 'comparison',
                        'status': 'active',
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    with open(os.path.join(session_folder, 'session.json'), 'w') as f:
                        json.dump(session_metadata, f, indent=2)
                        
                    logger.info(f"Session metadata saved locally for {session_id} (database fallback)")
                except Exception as fallback_error:
                    logger.error(f"Failed to save session metadata locally: {fallback_error}")
                    return jsonify({'error': 'Failed to create session'}), 500
        else:
            # Local mode: save session metadata to file
            try:
                session_folder = os.path.join('uploads', session_id)
                os.makedirs(session_folder, exist_ok=True)
                
                session_metadata = {
                    'id': session_id,
                    'session_type': 'comparison',
                    'status': 'active',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                with open(os.path.join(session_folder, 'session.json'), 'w') as f:
                    json.dump(session_metadata, f, indent=2)
                    
                logger.info(f"Session metadata saved locally for {session_id}")
            except Exception as e:
                logger.error(f"Failed to save session metadata locally: {e}")
                return jsonify({'error': 'Failed to create session'}), 500

        # Save uploaded files
        old_filename = secure_filename(old_file.filename)
        new_filename = secure_filename(new_file.filename)

        # Upload files to storage
        old_storage_path = f"sessions/{session_id}/old_{old_filename}"
        new_storage_path = f"sessions/{session_id}/new_{new_filename}"

        old_file.seek(0)  # Reset file pointer
        new_file.seek(0)

        old_url = storage_service.upload_file(old_file, old_storage_path)
        new_url = storage_service.upload_file(new_file, new_storage_path)

        # Save drawing records to database
        from gcp.database.models import Drawing
        old_drawing = Drawing(
            id=str(uuid.uuid4()),
            session_id=session_id,
            drawing_type='old',
            filename=old_filename,
            original_filename=old_file.filename,
            storage_path=old_storage_path,
            processed_at=datetime.now(timezone.utc)
        )

        new_drawing = Drawing(
            id=str(uuid.uuid4()),
            session_id=session_id,
            drawing_type='new',
            filename=new_filename,
            original_filename=new_file.filename,
            storage_path=new_storage_path,
            processed_at=datetime.now(timezone.utc)
        )

        # Save drawings to database if using database mode
        if config.USE_DATABASE:
            try:
                with get_db_session() as db:
                    db.add(old_drawing)
                    db.add(new_drawing)
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to save drawings to database: {e}")
                # Fallback to local mode if database fails
                logger.warning("Database unavailable for drawings, falling back to local mode")
                try:
                    drawings_metadata = {
                        'old_drawing': {
                            'id': str(uuid.uuid4()),
                            'session_id': session_id,
                            'drawing_type': 'old',
                            'filename': old_filename,
                            'original_filename': old_file.filename,
                            'storage_path': old_storage_path,
                            'processed_at': datetime.now(timezone.utc).isoformat()
                        },
                        'new_drawing': {
                            'id': str(uuid.uuid4()),
                            'session_id': session_id,
                            'drawing_type': 'new',
                            'filename': new_filename,
                            'original_filename': new_file.filename,
                            'storage_path': new_storage_path,
                            'processed_at': datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    with open(os.path.join('uploads', session_id, 'drawings.json'), 'w') as f:
                        json.dump(drawings_metadata, f, indent=2)
                        
                    logger.info(f"Drawing metadata saved locally for {session_id} (database fallback)")
                except Exception as fallback_error:
                    logger.error(f"Failed to save drawing metadata locally: {fallback_error}")
                    return jsonify({'error': 'Failed to save drawing records'}), 500
        else:
            # Local mode: save drawing metadata to file
            try:
                drawings_metadata = {
                    'old_drawing': {
                        'id': str(uuid.uuid4()),
                        'session_id': session_id,
                        'drawing_type': 'old',
                        'filename': old_filename,
                        'original_filename': old_file.filename,
                        'storage_path': old_storage_path,
                        'processed_at': datetime.now(timezone.utc).isoformat()
                    },
                    'new_drawing': {
                        'id': str(uuid.uuid4()),
                        'session_id': session_id,
                        'drawing_type': 'new',
                        'filename': new_filename,
                        'original_filename': new_file.filename,
                        'storage_path': new_storage_path,
                        'processed_at': datetime.now(timezone.utc).isoformat()
                    }
                }
                
                with open(os.path.join('uploads', session_id, 'drawings.json'), 'w') as f:
                    json.dump(drawings_metadata, f, indent=2)
                    
                logger.info(f"Drawing metadata saved locally for {session_id}")
            except Exception as e:
                logger.error(f"Failed to save drawing metadata locally: {e}")
                return jsonify({'error': 'Failed to save drawing records'}), 500

        logger.info(f"Files uploaded for session {session_id}: {old_filename}, {new_filename}")

        return jsonify({
            'session_id': session_id,
            'old_filename': old_filename,
            'new_filename': new_filename
        })

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _clear_session_results(session_id):
    """Clear existing results for a session to prevent duplicates during retry"""
    try:
        from gcp.database.models import Comparison, AnalysisResult
        with get_db_session() as db:
            # Delete existing analysis results for this session
            deleted_analyses = db.query(AnalysisResult).filter_by(session_id=session_id).delete()
            logger.info(f"Deleted {deleted_analyses} existing analysis results for session {session_id}")

            # Delete existing comparisons for this session
            deleted_comparisons = db.query(Comparison).filter_by(session_id=session_id).delete()
            logger.info(f"Deleted {deleted_comparisons} existing comparisons for session {session_id}")

            db.commit()
            return True

    except Exception as e:
        logger.error(f"Error clearing session results for {session_id}: {e}")
        return False


def _remove_duplicate_records(session_id):
    """Remove duplicate records from database for a specific session"""
    try:
        from gcp.database.models import Comparison, AnalysisResult
        from sqlalchemy import func

        with get_db_session() as db:
            # Find and remove duplicate analysis results
            # Keep only the first record for each (session_id, drawing_name) combination
            analysis_duplicates = db.query(AnalysisResult.id).filter_by(session_id=session_id).all()
            if len(analysis_duplicates) > 0:
                # Get unique drawing names
                unique_drawings = db.query(AnalysisResult.drawing_name).filter_by(session_id=session_id).distinct().all()
                drawing_names = [d[0] for d in unique_drawings]

                kept_ids = []
                for drawing_name in drawing_names:
                    # Keep the first record for each drawing
                    first_record = db.query(AnalysisResult).filter_by(
                        session_id=session_id, drawing_name=drawing_name
                    ).order_by(AnalysisResult.created_at).first()
                    if first_record:
                        kept_ids.append(first_record.id)

                # Delete all other records
                deleted_analyses = db.query(AnalysisResult).filter(
                    AnalysisResult.session_id == session_id,
                    ~AnalysisResult.id.in_(kept_ids)
                ).delete()

                logger.info(f"Removed {deleted_analyses} duplicate analysis results for session {session_id}")

            # Find and remove duplicate comparisons
            comparison_duplicates = db.query(Comparison.id).filter_by(session_id=session_id).all()
            if len(comparison_duplicates) > 0:
                # Get unique drawing names
                unique_comp_drawings = db.query(Comparison.drawing_name).filter_by(session_id=session_id).distinct().all()
                comp_drawing_names = [d[0] for d in unique_comp_drawings]

                kept_comp_ids = []
                for drawing_name in comp_drawing_names:
                    # Keep the first record for each drawing
                    first_comp = db.query(Comparison).filter_by(
                        session_id=session_id, drawing_name=drawing_name
                    ).order_by(Comparison.created_at).first()
                    if first_comp:
                        kept_comp_ids.append(first_comp.id)

                # Delete all other records
                deleted_comparisons = db.query(Comparison).filter(
                    Comparison.session_id == session_id,
                    ~Comparison.id.in_(kept_comp_ids)
                ).delete()

                logger.info(f"Removed {deleted_comparisons} duplicate comparisons for session {session_id}")

            db.commit()
            return True

    except Exception as e:
        logger.error(f"Error removing duplicates for session {session_id}: {e}")
        return False


def _store_results_to_database(session_id, results, old_storage_path, new_storage_path):
    """Helper function to store processing results to database"""
    try:
        from gcp.database.models import Session, Drawing, Comparison, AnalysisResult
        with get_db_session() as db:
            # Get the session
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                logger.error(f"Session {session_id} not found for result storage")
                return False

            # Get the drawings
            old_drawing = db.query(Drawing).filter_by(
                session_id=session_id,
                drawing_type='old'
            ).first()

            new_drawing = db.query(Drawing).filter_by(
                session_id=session_id,
                drawing_type='new'
            ).first()

            # Create Comparison records from results
            comparison_results = results.get('comparison_results', {})
            overlay_folders = results.get('overlay_folders', [])
            analysis_results = results.get('analysis_results', [])

            # Map drawing names to comparisons for analysis linkage
            comparison_map = {}

            # Process each overlay folder to create comparison records
            base_overlay_dir = results.get('summary', {}).get('base_overlay_directory', '')
            if base_overlay_dir and os.path.exists(base_overlay_dir):
                for folder_name in sorted(os.listdir(base_overlay_dir)):
                    if os.path.isdir(os.path.join(base_overlay_dir, folder_name)) and 'overlay_results' in folder_name:
                        drawing_name = folder_name.replace('_overlay_results', '')
                        folder_path = os.path.join(base_overlay_dir, folder_name)

                        overlay_path = None
                        old_image_path = None
                        new_image_path = None

                        for file_name in os.listdir(folder_path):
                            file_path = os.path.join(folder_path, file_name)
                            if file_name == f"{drawing_name}_overlay.png":
                                cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                overlay_path = storage_service.upload_from_filename(file_path, cloud_path) or file_path
                            elif file_name == f"{drawing_name}_old.png":
                                cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                old_image_path = storage_service.upload_from_filename(file_path, cloud_path) or file_path
                            elif file_name == f"{drawing_name}_new.png":
                                cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                new_image_path = storage_service.upload_from_filename(file_path, cloud_path) or file_path
                            elif file_name == f"change_analysis_{drawing_name}.json":
                                cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                json_path = storage_service.upload_from_filename(file_path, cloud_path)
                                logger.info(f"Uploaded analysis JSON to: {json_path}")

                        # Create or update comparison record (upsert logic)
                        existing_comparison = db.query(Comparison).filter_by(
                            session_id=session_id, drawing_name=drawing_name
                        ).first()

                        if existing_comparison:
                            # Update existing comparison
                            existing_comparison.overlay_path = overlay_path
                            existing_comparison.old_image_path = old_image_path
                            existing_comparison.new_image_path = new_image_path
                            existing_comparison.alignment_score = 1.0
                            existing_comparison.changes_detected = True if overlay_path else False
                            comparison = existing_comparison
                            logger.info(f"Updated existing comparison for {drawing_name}")
                        else:
                            # Create new comparison
                            comparison = Comparison(
                                id=str(uuid.uuid4()),
                                session_id=session_id,
                                old_drawing_id=old_drawing.id if old_drawing else None,
                                new_drawing_id=new_drawing.id if new_drawing else None,
                                drawing_name=drawing_name,
                                overlay_path=overlay_path,
                                old_image_path=old_image_path,
                                new_image_path=new_image_path,
                                alignment_score=1.0,
                                changes_detected=True if overlay_path else False,
                                created_at=datetime.now(timezone.utc)
                            )
                            db.add(comparison)
                            logger.info(f"Created new comparison for {drawing_name}")

                        comparison_map[drawing_name] = comparison

            # Create AnalysisResult records if AI analysis was performed
            if analysis_results:
                for analysis_data in analysis_results:
                    if isinstance(analysis_data, ChangeAnalysisResult):
                        analysis_dict = analysis_data.to_dict()
                    elif isinstance(analysis_data, dict):
                        analysis_dict = analysis_data
                    else:
                        continue

                    drawing_name = analysis_dict.get('drawing_name', '')
                    comparison = comparison_map.get(drawing_name)

                    if comparison:
                        # Create or update analysis result (upsert logic)
                        existing_analysis = db.query(AnalysisResult).filter_by(
                            session_id=session_id, drawing_name=drawing_name
                        ).first()

                        if existing_analysis:
                            # Update existing analysis
                            existing_analysis.comparison_id = comparison.id
                            existing_analysis.changes_found = analysis_dict.get('changes_found', [])
                            existing_analysis.critical_change = analysis_dict.get('critical_change')
                            existing_analysis.analysis_summary = analysis_dict.get('analysis_summary')
                            existing_analysis.recommendations = analysis_dict.get('recommendations', [])
                            existing_analysis.success = analysis_dict.get('success', True)
                            existing_analysis.error_message = analysis_dict.get('error_message')
                            existing_analysis.ai_model_used = 'gpt-4-vision-preview'
                            logger.info(f"Updated existing analysis for {drawing_name}")
                        else:
                            # Create new analysis
                            analysis_result = AnalysisResult(
                                id=str(uuid.uuid4()),
                                comparison_id=comparison.id,
                                session_id=session_id,
                                drawing_name=drawing_name,
                                changes_found=analysis_dict.get('changes_found', []),
                                critical_change=analysis_dict.get('critical_change'),
                                analysis_summary=analysis_dict.get('analysis_summary'),
                                recommendations=analysis_dict.get('recommendations', []),
                                success=analysis_dict.get('success', True),
                                error_message=analysis_dict.get('error_message'),
                                ai_model_used='gpt-4-vision-preview',
                                created_at=datetime.now(timezone.utc)
                            )
                            db.add(analysis_result)
                            logger.info(f"Created new analysis for {drawing_name}")

            db.commit()

            # Create chatbot-compatible results.json file
            chatbot_uploads_dir = os.path.join('uploads', session_id)
            os.makedirs(chatbot_uploads_dir, exist_ok=True)

            chatbot_results = {
                'output_directories': results.get('output_directories', [])
            }

            chatbot_results_file = os.path.join(chatbot_uploads_dir, 'results.json')
            with open(chatbot_results_file, 'w') as f:
                json.dump(chatbot_results, f, indent=2)

            logger.info(f"Created chatbot results file: {chatbot_results_file}")
            return True

    except Exception as e:
        logger.error(f"Failed to store results to database: {e}")
        return False


@app.route('/process/<session_id>', methods=['POST'])
def process_drawings(session_id):
    """Process the uploaded drawings"""
    try:
        # Get session and drawings from database - keep everything in one session context
        from gcp.database.models import Session, Drawing

        if not config.USE_DATABASE:
            return jsonify({'error': 'Database mode required for processing'}), 400

        with get_db_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404

            drawings = db.query(Drawing).filter_by(session_id=session_id).all()
            old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
            new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

            if not old_drawing or not new_drawing:
                return jsonify({'error': 'Uploaded files not found'}), 404

            # Update session status to processing
            session.status = 'processing'
            db.commit()

            # Extract the data we need before the session closes
            old_storage_path = old_drawing.storage_path
            old_filename = old_drawing.filename
            new_storage_path = new_drawing.storage_path
            new_filename = new_drawing.filename

        # Process based on configuration
        if config.USE_ASYNC_PROCESSING or config.USE_BACKGROUND_PROCESSING:
            # Use Cloud Tasks for background processing (Cloud Run compatible)
            try:
                from gcp.tasks import task_processor

                # Update session status to processing
                if config.USE_DATABASE:
                    with get_db_session() as db:
                        session = db.query(Session).filter_by(id=session_id).first()
                        if session:
                            session.status = 'processing'
                            session.updated_at = datetime.utcnow()
                            if not session.session_metadata:
                                session.session_metadata = {}
                            session.session_metadata['current_step'] = 'queued'
                            session.session_metadata['processing_started'] = datetime.utcnow().isoformat()
                            db.commit()

                # Create Cloud Task for processing
                task_name = task_processor.create_processing_task(
                    session_id=session_id,
                    old_path=old_storage_path,
                    new_path=new_storage_path,
                    old_name=old_filename,
                    new_name=new_filename
                )

                logger.info(f"Created Cloud Task for session {session_id}: {task_name}")

                # Return immediately with session ID for polling
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'status': 'processing',
                    'task_name': task_name,
                    'message': 'Files uploaded successfully. Processing queued...'
                })

            except Exception as e:
                logger.error(f"Failed to create Cloud Task for session {session_id}: {e}")
                # Fall back to synchronous processing
                logger.info(f"Falling back to synchronous processing for session {session_id}")

                # Update session status to processing
                if config.USE_DATABASE:
                    with get_db_session() as db:
                        session = db.query(Session).filter_by(id=session_id).first()
                        if session:
                            session.status = 'processing'
                            session.updated_at = datetime.utcnow()
                            session.session_metadata = {'fallback_to_sync': True, 'error': str(e)}
                            db.commit()

        # Synchronous processing (either as default or fallback)
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download files to temp directory
            old_temp_path = os.path.join(temp_dir, old_filename)
            new_temp_path = os.path.join(temp_dir, new_filename)

            if not storage_service.download_to_filename(old_storage_path, old_temp_path):
                return jsonify({'error': 'Failed to download old file'}), 500

            if not storage_service.download_to_filename(new_storage_path, new_temp_path):
                return jsonify({'error': 'Failed to download new file'}), 500

            # Use chunked processor for large files to get proper statistics
            results = chunked_process_documents(
                old_pdf_path=old_temp_path,
                new_pdf_path=new_temp_path,
                session_id=session_id
            )

            # Store results
            if results['success']:
                # Update session in database with results (only if database is enabled)
                if config.USE_DATABASE:
                    with get_db_session() as db:
                        session = db.query(Session).filter_by(id=session_id).first()
                        if session:
                            session.status = 'completed'
                            session.total_time = results.get('summary', {}).get('total_time', 0.0)
                            # Clear cache when session is completed
                            recent_sessions_cache.clear('recent_sessions')
                            # Serialize results to handle ChangeAnalysisResult objects
                            serialized_results = serialize_results_for_json(results)
                            session.session_metadata = {'results': serialized_results}
                            session.updated_at = datetime.now(timezone.utc)

                        # Create Drawing records for old and new PDFs
                        old_drawing = Drawing(
                            id=str(uuid.uuid4()),
                            session_id=session_id,
                            filename=old_filename,
                            original_filename=old_filename,
                            storage_path=old_storage_path,
                            drawing_type='old',
                            processed_at=datetime.now(timezone.utc)
                        )
                        new_drawing = Drawing(
                            id=str(uuid.uuid4()),
                            session_id=session_id,
                            filename=new_filename,
                            original_filename=new_filename,
                            storage_path=new_storage_path,
                            drawing_type='new',
                            processed_at=datetime.now(timezone.utc)
                        )
                        db.add(old_drawing)
                        db.add(new_drawing)

                        # Create Comparison records from results
                        comparison_results = results.get('comparison_results', {})
                        overlay_folders = results.get('overlay_folders', [])
                        analysis_results = results.get('analysis_results', [])

                        # Map drawing names to comparisons for analysis linkage
                        comparison_map = {}

                        # Process each overlay folder to create comparison records
                        base_overlay_dir = results.get('summary', {}).get('base_overlay_directory', '')
                        if base_overlay_dir and os.path.exists(base_overlay_dir):
                            for folder_name in sorted(os.listdir(base_overlay_dir)):
                                if os.path.isdir(os.path.join(base_overlay_dir, folder_name)) and 'overlay_results' in folder_name:
                                    drawing_name = folder_name.replace('_overlay_results', '')
                                    folder_path = os.path.join(base_overlay_dir, folder_name)

                                    # Find the overlay, old, and new image paths and upload to cloud storage
                                    overlay_path = None
                                    old_image_path = None
                                    new_image_path = None

                                    for file_name in os.listdir(folder_path):
                                        file_path = os.path.join(folder_path, file_name)
                                        if file_name == f"{drawing_name}_overlay.png":
                                            # Upload to cloud storage and get cloud path
                                            cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                            overlay_path = storage_service.upload_from_filename(file_path, cloud_path) or file_path
                                        elif file_name == f"{drawing_name}_old.png":
                                            cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                            old_image_path = storage_service.upload_from_filename(file_path, cloud_path) or file_path
                                        elif file_name == f"{drawing_name}_new.png":
                                            cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                            new_image_path = storage_service.upload_from_filename(file_path, cloud_path) or file_path
                                        elif file_name == f"change_analysis_{drawing_name}.json":
                                            # Upload the JSON analysis file to cloud storage
                                            cloud_path = f"sessions/{session_id}/results/{drawing_name}/{file_name}"
                                            json_path = storage_service.upload_from_filename(file_path, cloud_path)
                                            logger.info(f"Uploaded analysis JSON to: {json_path}")

                                    # Create comparison record
                                    comparison = Comparison(
                                        id=str(uuid.uuid4()),
                                        session_id=session_id,
                                        old_drawing_id=old_drawing.id,
                                        new_drawing_id=new_drawing.id,
                                        drawing_name=drawing_name,
                                        overlay_path=overlay_path,
                                        old_image_path=old_image_path,
                                        new_image_path=new_image_path,
                                        alignment_score=1.0,  # Could extract from results if available
                                        changes_detected=True if overlay_path else False,
                                        created_at=datetime.now(timezone.utc)
                                    )
                                    db.add(comparison)
                                    comparison_map[drawing_name] = comparison

                        # Create AnalysisResult records if AI analysis was performed
                        if analysis_results:
                            for analysis_data in analysis_results:
                                # Handle both ChangeAnalysisResult objects and dictionaries
                                if isinstance(analysis_data, ChangeAnalysisResult):
                                    # Convert ChangeAnalysisResult object to dictionary
                                    analysis_dict = analysis_data.to_dict()
                                elif isinstance(analysis_data, dict):
                                    # Already a dictionary
                                    analysis_dict = analysis_data
                                else:
                                    # Skip invalid data
                                    continue

                                drawing_name = analysis_dict.get('drawing_name', '')
                                comparison = comparison_map.get(drawing_name)

                                if comparison:
                                    analysis_result = AnalysisResult(
                                        id=str(uuid.uuid4()),
                                        comparison_id=comparison.id,
                                        session_id=session_id,
                                        drawing_name=drawing_name,
                                        changes_found=analysis_dict.get('changes_found', []),
                                        critical_change=analysis_dict.get('critical_change'),
                                        analysis_summary=analysis_dict.get('analysis_summary'),
                                        recommendations=analysis_dict.get('recommendations', []),
                                        success=analysis_dict.get('success', True),
                                        error_message=analysis_dict.get('error_message'),
                                        ai_model_used='gpt-4-vision-preview',
                                        created_at=datetime.now(timezone.utc)
                                    )
                                    db.add(analysis_result)

                        db.commit()

                # Create chatbot-compatible results.json file
                chatbot_uploads_dir = os.path.join('uploads', session_id)
                os.makedirs(chatbot_uploads_dir, exist_ok=True)

                chatbot_results = {
                    'output_directories': results.get('output_directories', [])
                }

                chatbot_results_file = os.path.join(chatbot_uploads_dir, 'results.json')
                with open(chatbot_results_file, 'w') as f:
                    json.dump(chatbot_results, f, indent=2)

                logger.info(f"Created chatbot results file: {chatbot_results_file}")

                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'overlays_created': results['summary']['overlays_created'],
                    'analyses_completed': results['summary']['analyses_completed'],
                    'output_directory': results['summary'].get('base_overlay_directory', ''),
                    'processing_time': results['summary']['total_time']
                })
            else:
                # Update session status to error in database
                if config.USE_DATABASE:
                    with get_db_session() as db:
                        session = db.query(Session).filter_by(id=session_id).first()
                        if session:
                            session.status = 'error'
                            db.commit()
                return jsonify({
                    'success': False,
                    'error': results.get('error', 'Unknown error occurred')
                }), 500

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        # Update session status to error in database
        try:
            if config.USE_DATABASE:
                with get_db_session() as db:
                    session = db.query(Session).filter_by(id=session_id).first()
                    if session:
                        session.status = 'error'
                        db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update session status: {db_error}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/status/<session_id>')
def get_status(session_id):
    """Get processing status (cloud mode only)"""
    if not config.USE_DATABASE:
        return jsonify({'error': 'Status endpoint only available in cloud mode'}), 404

    try:
        from gcp.database.models import Session

        with get_db_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404

            return jsonify({
                'session_id': session_id,
                'status': session.status,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'total_time': session.total_time
            })

    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/results/<session_id>')
def view_results(session_id):
    """Display results page"""
    try:
        from gcp.database.models import Session

        results_data = None

        if config.USE_DATABASE:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return "Session not found", 404

                # Extract the results data while within the session context
                if session.session_metadata:
                    results_data = session.session_metadata.get('results')
        else:
            return "Database mode required for results viewing", 400

        # For local mode, try to load from file system as fallback
        if not config.USE_DATABASE and results_data is None:
            results_file = os.path.join(config.LOCAL_UPLOAD_PATH, session_id, 'results.json')
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    results_data = json.load(f)

        # Provide default structure if results are not available yet
        if results_data is None:
            # Check session status if available
            session_status = 'unknown'
            if config.USE_DATABASE:
                with get_db_session() as db:
                    session = db.query(Session).filter_by(id=session_id).first()
                    if session:
                        session_status = session.status

            # Provide default results structure for template
            results_data = {
                'summary': {
                    'overlays_created': 0,
                    'analyses_completed': 0,
                    'total_time': 0
                },
                'status': session_status,
                'message': 'Processing in progress...' if session_status == 'processing' else 'No results available'
            }

        # Ensure summary exists and has all required fields
        if 'summary' not in results_data:
            results_data['summary'] = {}

        # Ensure all required summary fields exist
        summary_defaults = {
            'overlays_created': 0,
            'analyses_completed': 0,
            'total_time': 0,
            'added_drawings': 0
        }

        for key, default_value in summary_defaults.items():
            if key not in results_data['summary']:
                results_data['summary'][key] = default_value

        return render_template('results.html',
                             session_id=session_id,
                             results=results_data)

    except Exception as e:
        logger.error(f"Results view error: {str(e)}")
        return f"Error loading results: {str(e)}", 500

@app.route('/api/changes/<session_id>')
def get_changes(session_id):
    """API endpoint to get changes data"""
    try:
        # This implementation is from the updated app_original.py
        # It reads the analysis JSON files directly for meaningful data
        from gcp.database.models import Session

        session_metadata = None
        if config.USE_DATABASE:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404
                session_metadata = session.session_metadata

        changes = []

        # For local mode, read from session-specific results
        if not config.USE_DATABASE:
            # First try to get results from session metadata
            if session_metadata and session_metadata.get('results'):
                results = session_metadata.get('results', {})
                output_directories = results.get('output_directories', [])
                
                # Process each output directory from the session
                for i, output_dir in enumerate(output_directories):
                    if not os.path.exists(output_dir) or 'overlay_results' not in output_dir:
                        continue
                    
                    # Look for change_analysis_*.json files in this specific directory
                    for file_name in os.listdir(output_dir):
                        if file_name.startswith('change_analysis_') and file_name.endswith('.json'):
                            analysis_file = os.path.join(output_dir, file_name)
                        
                            try:
                                with open(analysis_file, 'r') as f:
                                    analysis_data = json.load(f)
                                
                                if not analysis_data.get('success', False):
                                    continue
                                
                                # Extract drawing name from filename or data
                                drawing_name = analysis_data.get('drawing_name', '')
                                if not drawing_name:
                                    # Extract from filename like change_analysis_A-111.json
                                    drawing_name = file_name.replace('change_analysis_', '').replace('.json', '')
                                
                                # Use the restructuring function to get better organized data
                                restructured_data = restructure_analysis_data(analysis_data)
                                
                                changes.append({
                                    'id': len(changes) + 1,
                                    'drawing_number': drawing_name,
                                    'critical_change': restructured_data['critical_change'],
                                    'changes_breakdown': restructured_data['changes_breakdown'],
                                    'impact_analysis': restructured_data['impact_analysis'],
                                    'recommendations': restructured_data['recommendations'],
                                    'construction_impact': restructured_data['construction_impact']
                                })
                                
                            except Exception as e:
                                logger.warning(f"Error processing analysis file {analysis_file}: {e}")
                                continue
            else:
                # Fallback: if no session metadata, return empty results
                logger.warning(f"No session metadata found for session {session_id}")
                return jsonify({'changes': []})

        else:
            # Database-based changes retrieval - try both JSON files and database

            # First try to read JSON files from Cloud Storage
            try:
                from gcp.storage import storage_service

                # List all JSON files for this session
                blob_prefix = f"sessions/{session_id}/results/"
                file_paths = storage_service.list_files(prefix=blob_prefix)

                for file_path in file_paths:
                    if 'change_analysis_' in file_path and file_path.endswith('.json'):
                        try:
                            # Download and parse JSON
                            json_bytes = storage_service.download_file(file_path)
                            json_content = json_bytes.decode('utf-8')
                            analysis_data = json.loads(json_content)

                            if not analysis_data.get('success', False):
                                continue

                            drawing_name = analysis_data.get('drawing_name', '')
                            if not drawing_name:
                                # Extract from filename
                                filename = file_path.split('/')[-1]
                                drawing_name = filename.replace('change_analysis_', '').replace('.json', '')

                            changes.append({
                                'id': len(changes) + 1,
                                'drawing_number': drawing_name,
                                'description': analysis_data.get('critical_change', 'Changes detected'),
                                'critical_change': {
                                    'content': analysis_data.get('critical_change', 'Changes detected'),
                                    'title': 'Most Critical Change'
                                },
                                'details': analysis_data.get('changes_found', []),
                                'summary': analysis_data.get('analysis_summary', ''),
                                'recommendations': analysis_data.get('recommendations', [])
                            })

                        except Exception as e:
                            logger.warning(f"Error processing JSON file {file_path}: {e}")
                            continue

            except Exception as e:
                logger.warning(f"Error reading JSON files from Cloud Storage: {e}")

            # If no changes found from JSON files, fallback to database
            if not changes:
                with get_db_session() as db:
                    analyses = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).all()
                    for i, analysis in enumerate(analyses):
                        changes.append({
                            'id': i + 1,
                            'drawing_number': analysis.drawing_name,
                            'description': analysis.critical_change or 'Changes detected',
                            'critical_change': {
                                'content': analysis.critical_change or 'Changes detected',
                                'title': 'Most Critical Change'
                            },
                            'details': analysis.changes_found or [],
                            'summary': analysis.analysis_summary or '',
                            'recommendations': analysis.recommendations or []
                        })

        return jsonify({'changes': changes})

    except Exception as e:
        logger.error(f"Changes API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/status')
def get_session_status(session_id):
    """Get the current status of a session processing"""
    try:
        if config.USE_DATABASE:
            from gcp.database.models import Session
            from datetime import datetime, timedelta

            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404

                # Check for timeout if session is still processing
                if session.status == 'processing':
                    now = datetime.utcnow()
                    time_since_created = now - session.created_at.replace(tzinfo=None)
                    time_since_updated = now - session.updated_at.replace(tzinfo=None)

                    hours_processing = time_since_created.total_seconds() / 3600
                    minutes_no_update = time_since_updated.total_seconds() / 60

                    # Smart timeout detection based on progress indicators
                    is_likely_stuck = False
                    stuck_reason = None

                    # Check for progress indicators in session metadata
                    metadata = session.session_metadata or {}
                    pages_count = metadata.get('pages_count', 0)
                    pages_processed = metadata.get('pages_processed', 0)
                    current_step = metadata.get('current_step', 'unknown')
                    last_progress_update = metadata.get('last_progress_update')

                    # Calculate expected processing time based on file size
                    # Typical processing: ~2-3 minutes per page for full pipeline
                    expected_minutes = max(30, pages_count * 3)  # At least 30 minutes, 3 min/page
                    expected_hours = expected_minutes / 60

                    # Determine if stuck based on intelligent criteria
                    if minutes_no_update > 60 and pages_count <= 1:
                        # Single page should never take more than 60 minutes without updates
                        is_likely_stuck = True
                        stuck_reason = f"Single-page upload stuck for {minutes_no_update:.0f} minutes"
                    elif minutes_no_update > 120:
                        # No updates for 2+ hours is always concerning
                        is_likely_stuck = True
                        stuck_reason = f"No progress updates for {minutes_no_update:.0f} minutes"
                    elif hours_processing > max(6, expected_hours * 2):
                        # Taking more than 2x expected time or 6 hours (whichever is larger)
                        is_likely_stuck = True
                        stuck_reason = f"Processing time ({hours_processing:.1f}h) exceeds 2x expected ({expected_hours:.1f}h)"
                    elif pages_processed > 0 and pages_processed == metadata.get('last_pages_processed', 0):
                        # Pages processed hasn't changed in a while
                        last_change = metadata.get('last_pages_processed_time')
                        if last_change:
                            try:
                                last_change_time = datetime.fromisoformat(last_change)
                                minutes_since_progress = (now - last_change_time).total_seconds() / 60
                                if minutes_since_progress > 45:
                                    is_likely_stuck = True
                                    stuck_reason = f"No new pages processed for {minutes_since_progress:.0f} minutes"
                            except:
                                pass

                    # Auto-mark as failed only if we're confident it's stuck
                    if is_likely_stuck:
                        logger.warning(f"Session {session_id} likely stuck: {stuck_reason}")

                        # Update status to error
                        session.status = 'error'
                        session.updated_at = now
                        if not session.session_metadata:
                            session.session_metadata = {}
                        session.session_metadata['error'] = f'Processing timeout: {stuck_reason}'
                        session.session_metadata['timeout_detected'] = now.isoformat()
                        session.session_metadata['processing_stats'] = {
                            'hours_processing': hours_processing,
                            'minutes_no_update': minutes_no_update,
                            'pages_count': pages_count,
                            'pages_processed': pages_processed,
                            'last_step': current_step
                        }
                        db.commit()

                response = {
                    'session_id': session_id,
                    'status': session.status,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                    'total_time': session.total_time
                }

                # Add processing time info for active sessions
                if session.status in ['processing', 'error']:
                    now = datetime.utcnow()
                    time_since_created = now - session.created_at.replace(tzinfo=None)
                    time_since_updated = now - session.updated_at.replace(tzinfo=None)

                    response['processing_time'] = {
                        'hours_since_created': round(time_since_created.total_seconds() / 3600, 1),
                        'minutes_since_update': round(time_since_updated.total_seconds() / 60, 1)
                    }

                # Add additional info based on status
                if session.status == 'completed':
                    # Get summary statistics
                    from gcp.database.models import Comparison, AnalysisResult

                    comparisons_count = db.query(Comparison).filter_by(session_id=session_id).count()
                    analyses_count = db.query(AnalysisResult).filter_by(session_id=session_id).count()

                    response['summary'] = {
                        'overlays_created': comparisons_count,
                        'analyses_completed': analyses_count
                    }
                elif session.status == 'error':
                    # Include error message if available
                    if session.session_metadata and 'error' in session.session_metadata:
                        response['error'] = session.session_metadata['error']

                return jsonify(response)
        else:
            # For local mode, check if results exist
            results_file = os.path.join(config.LOCAL_UPLOAD_PATH, session_id, 'results.json')
            if os.path.exists(results_file):
                return jsonify({
                    'session_id': session_id,
                    'status': 'completed'
                })
            else:
                return jsonify({
                    'session_id': session_id,
                    'status': 'processing'
                })

    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/retry', methods=['POST'])
def retry_session_processing(session_id):
    """Retry processing for a failed or stuck session"""
    try:
        if not config.USE_DATABASE:
            return jsonify({'error': 'Retry functionality requires database mode'}), 400

        from gcp.database.models import Session, Drawing
        from gcp.storage.storage_service import storage_service

        with get_db_session() as db:
            # Get the session
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404

            # Check if session can be retried
            if session.status not in ['error', 'processing']:
                return jsonify({'error': f'Cannot retry session with status: {session.status}'}), 400

            # Get original drawings from the session
            drawings = db.query(Drawing).filter_by(session_id=session_id).all()
            if len(drawings) < 2:
                return jsonify({'error': 'Original drawings not found for retry'}), 400

            # Find old and new drawings
            old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
            new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

            if not old_drawing or not new_drawing:
                return jsonify({'error': 'Missing old or new drawing for retry'}), 400

            # Reset session status
            session.status = 'processing'
            session.updated_at = datetime.now()
            if session.session_metadata:
                session.session_metadata.pop('error', None)  # Clear previous error
            db.commit()

            logger.info(f"Retrying processing for session {session_id}")

            # Use Cloud Tasks for retry processing (Cloud Run compatible)
            try:
                from gcp.tasks import task_processor

                # Create Cloud Task for retry processing
                task_name = task_processor.create_processing_task(
                    session_id=session_id,
                    old_path=old_drawing.storage_path,
                    new_path=new_drawing.storage_path,
                    old_name=old_drawing.filename,
                    new_name=new_drawing.filename
                )

                logger.info(f"Created retry Cloud Task for session {session_id}: {task_name}")

                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'status': 'processing',
                    'task_name': task_name,
                    'message': 'Session retry queued. Processing will start shortly...'
                })

            except Exception as e:
                logger.error(f"Failed to create retry Cloud Task for session {session_id}: {e}")
                return jsonify({'error': f'Failed to queue retry: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Error retrying session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/cleanup-duplicates', methods=['POST'])
def cleanup_session_duplicates(session_id):
    """Clean up duplicate records for a specific session"""
    try:
        success = _remove_duplicate_records(session_id)
        if success:
            return jsonify({
                'success': True,
                'message': f'Cleaned up duplicate records for session {session_id}'
            })
        else:
            return jsonify({'error': 'Failed to clean up duplicates'}), 500
    except Exception as e:
        logger.error(f"Error cleaning up duplicates for session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/drawings/<session_id>')
def get_drawing_images(session_id):
    """Get available drawing images for comparison view"""
    try:
        from gcp.database.models import Session

        session_metadata = None
        if config.USE_DATABASE:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404
                session_metadata = session.session_metadata

        drawing_comparisons = []

        # For local mode, read from file system
        if not config.USE_DATABASE and session_metadata:
            results = session_metadata.get('results', {})
            base_overlay_dir = results.get('summary', {}).get('base_overlay_directory', '')

            if base_overlay_dir and os.path.exists(base_overlay_dir):
                for folder_name in sorted(os.listdir(base_overlay_dir)):
                    folder_path = os.path.join(base_overlay_dir, folder_name)
                    if os.path.isdir(folder_path) and 'overlay_results' in folder_name:
                        drawing_name = folder_name.replace('_overlay_results', '')

                        comparison = {
                            'drawing_name': drawing_name,
                            'old_image': None,
                            'new_image': None,
                            'overlay_image': None
                        }

                        for file_name in os.listdir(folder_path):
                            if file_name.endswith(('.png', '.jpg', '.jpeg')):
                                file_path = os.path.join(folder_path, file_name)
                                if file_name == f"{drawing_name}_old.png":
                                    comparison['old_image'] = f"/files/{file_path}"
                                elif file_name == f"{drawing_name}_new.png":
                                    comparison['new_image'] = f"/files/{file_path}"
                                elif file_name == f"{drawing_name}_overlay.png":
                                    comparison['overlay_image'] = f"/files/{file_path}"

                        if comparison['overlay_image']:
                            drawing_comparisons.append(comparison)
        else:
            # Database mode - read from comparisons table
            with get_db_session() as db:
                comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
                for comparison in comparisons:
                    # Build URLs for images
                    old_image = None
                    new_image = None
                    overlay_image = None

                    # Generate /image/ URLs - encode GCS paths to avoid URL issues
                    if comparison.old_image_path:
                        import urllib.parse
                        encoded_path = urllib.parse.quote(comparison.old_image_path, safe='')
                        old_image = f"/image/{encoded_path}"
                        logger.info(f"Using encoded image route for old image: {old_image}")

                    if comparison.new_image_path:
                        import urllib.parse
                        encoded_path = urllib.parse.quote(comparison.new_image_path, safe='')
                        new_image = f"/image/{encoded_path}"
                        logger.info(f"Using encoded image route for new image: {new_image}")

                    if comparison.overlay_path:
                        import urllib.parse
                        encoded_path = urllib.parse.quote(comparison.overlay_path, safe='')
                        overlay_image = f"/image/{encoded_path}"
                        logger.info(f"Using encoded image route for overlay image: {overlay_image}")

                    drawing_comparisons.append({
                        'drawing_name': comparison.drawing_name,
                        'old_image': old_image,
                        'new_image': new_image,
                        'overlay_image': overlay_image
                    })

        # Provide detailed status information
        status_info = {}
        if session_metadata and session_metadata.get('results'):
            results = session_metadata.get('results', {})
            summary = results.get('summary', {})
            status_info = {
                'overlays_created': summary.get('overlays_created', 0),
                'overlays_failed': summary.get('overlays_failed', 0),
                'processing_status': summary.get('status', 'unknown'),
                'error_message': summary.get('error_message', None)
            }

        return jsonify({
            'comparisons': drawing_comparisons,
            'status': status_info,
            'has_overlays': len(drawing_comparisons) > 0
        })

    except Exception as e:
        logger.error(f"Drawings API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# File serving routes
@app.route('/files/<path:file_path>')
def serve_file(file_path):
    """Serve files from storage (local mode)"""
    if not config.USE_GCS:
        try:
            # For local storage, serve files directly
            abs_path = os.path.abspath(file_path)
            project_dir = os.path.abspath('.')

            if not abs_path.startswith(project_dir):
                return "Access denied", 403

            if os.path.exists(abs_path):
                directory = os.path.dirname(abs_path)
                filename = os.path.basename(abs_path)
                return send_from_directory(directory, filename)
            else:
                return "File not found", 404

        except Exception as e:
            return f"Error serving file: {str(e)}", 500
    else:
        # For GCS, redirect to signed URL
        signed_url = storage_service.get_signed_url(file_path)
        if signed_url:
            return jsonify({'url': signed_url})
        else:
            return "File not found", 404

@app.route('/image/<path:image_path>')
def serve_image(image_path):
    """Serve images from GCS using direct client"""
    try:
        # Decode the URL-encoded path
        import urllib.parse
        decoded_path = urllib.parse.unquote(image_path)
        logger.info(f"Serving image - original: {image_path}, decoded: {decoded_path}")

        # Handle GCS paths
        if decoded_path.startswith('gs://'):
            # Extract blob path from full GCS URI
            parts = decoded_path[5:].split('/', 1)  # Remove 'gs://'
            if len(parts) == 2:
                bucket_name, blob_path = parts
                logger.info(f"Downloading from GCS bucket: {bucket_name}, path: {blob_path}")

                try:
                    # Create a direct GCS client with default credentials
                    from google.cloud import storage
                    client = storage.Client()
                    bucket = client.bucket(bucket_name)
                    blob = bucket.blob(blob_path)

                    # Download image data
                    image_data = blob.download_as_bytes()

                    # Determine content type
                    content_type = 'image/png'
                    if blob_path.lower().endswith('.jpg') or blob_path.lower().endswith('.jpeg'):
                        content_type = 'image/jpeg'
                    elif blob_path.lower().endswith('.png'):
                        content_type = 'image/png'

                    logger.info(f"Successfully serving GCS image: {blob_path} ({len(image_data)} bytes)")
                    import io
                    return send_file(
                        io.BytesIO(image_data),
                        mimetype=content_type,
                        as_attachment=False
                    )
                except Exception as gcs_error:
                    logger.error(f"Failed to download from GCS: {gcs_error}")
                    logger.error(f"Exception type: {type(gcs_error).__name__}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    return f"Failed to load image from GCS: {str(gcs_error)}", 500
            else:
                logger.error(f"Invalid GCS URI format: {decoded_path}")
                return "Invalid GCS URI format", 400

        # For non-GCS paths, return error since we only have GCS storage in production
        logger.error(f"Non-GCS path not supported in production: {decoded_path}")
        return "Only GCS images supported in production", 400

    except Exception as e:
        logger.error(f"Error serving image {image_path}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return f"Error serving image: {str(e)}", 500

@app.route('/download/<session_id>/<path:filename>')
def download_file(session_id, filename):
    """Download files from session"""
    try:
        if not config.USE_GCS:
            session_folder = os.path.join(config.LOCAL_UPLOAD_PATH, session_id)
            return send_from_directory(session_folder, filename, as_attachment=True)
        else:
            # TODO: Implement GCS download
            return jsonify({'error': 'GCS download not implemented yet'}), 501
    except Exception as e:
        return f"File not found: {str(e)}", 404

# Cloud-only routes
if config.USE_DATABASE:
    @app.route('/api/debug/session/<session_id>')
    def debug_session(session_id):
        """Debug endpoint for session information"""
        try:
            from gcp.database.models import Session, Drawing, Comparison, AnalysisResult

            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404

                drawings = db.query(Drawing).filter_by(session_id=session_id).all()
                comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
                analyses = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).all()

                # Convert to dict but handle SQLAlchemy object serialization
                session_dict = {
                    'id': session.id,
                    'session_type': session.session_type,
                    'status': session.status,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                    'total_time': session.total_time,
                    'session_metadata': session.session_metadata
                }

                return jsonify({
                    'session': session_dict,
                    'drawings': [{'id': d.id, 'drawing_name': d.drawing_name, 'status': d.status} for d in drawings],
                    'comparisons': [{'id': c.id, 'drawing_name': c.drawing_name, 'status': c.status} for c in comparisons],
                    'analyses': [{'id': a.id, 'drawing_name': a.drawing_name, 'critical_change': a.critical_change} for a in analyses]
                })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/sessions/recent')
    def get_recent_sessions():
        """Get recent sessions with enhanced data for table display"""
        # Check cache first
        cache_key = 'recent_sessions'
        cached_data = recent_sessions_cache.get(cache_key)
        if cached_data:
            logger.info("Serving recent sessions from cache")
            return jsonify(cached_data)

        try:
            from gcp.database.models import Session, Drawing, AnalysisResult
            from sqlalchemy.orm import joinedload
            from sqlalchemy import func

            with get_db_session() as db:
                # Use eager loading to fetch sessions with their drawings in a single query
                sessions = db.query(Session)\
                    .options(joinedload(Session.drawings))\
                    .order_by(Session.created_at.desc())\
                    .limit(10)\
                    .all()

                # Get all analysis result counts in a single query
                session_ids = [s.id for s in sessions]
                analysis_counts = {}
                if session_ids:
                    count_results = db.query(
                        AnalysisResult.session_id,
                        func.count(AnalysisResult.id).label('count')
                    ).filter(
                        AnalysisResult.session_id.in_(session_ids)
                    ).group_by(
                        AnalysisResult.session_id
                    ).all()

                    analysis_counts = {r.session_id: r.count for r in count_results}

                session_list = []
                for s in sessions:
                    # Drawings are already loaded via eager loading
                    old_drawing = next((d for d in s.drawings if d.drawing_type == 'old'), None)
                    new_drawing = next((d for d in s.drawings if d.drawing_type == 'new'), None)

                    # Get analysis count from our pre-fetched dictionary
                    analysis_count = analysis_counts.get(s.id, 0)

                    # Extract change count from analysis results
                    changes_detected = 0
                    if s.session_metadata and 'results' in s.session_metadata:
                        try:
                            results = s.session_metadata['results']
                            if 'changes' in results:
                                changes_detected = len(results['changes'])
                            elif 'analysis_results' in results:
                                changes_detected = len(results['analysis_results'])
                        except (TypeError, KeyError):
                            pass

                    # Fallback: count from database if metadata is empty
                    if changes_detected == 0:
                        changes_detected = analysis_count

                    session_data = {
                        'id': s.id,
                        'status': s.status,
                        'created_at': s.created_at.isoformat() if s.created_at else None,
                        'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                        'total_time': s.total_time,
                        'baseline_filename': old_drawing.original_filename if old_drawing else 'N/A',
                        'revised_filename': new_drawing.original_filename if new_drawing else 'N/A',
                        'changes_count': changes_detected,
                        'has_drawings': len(s.drawings) > 0,
                        'drawing_count': len(s.drawings)
                    }
                    session_list.append(session_data)

                # Cache the result before returning
                result = {'sessions': session_list}
                recent_sessions_cache.set(cache_key, result)
                logger.info(f"Cached {len(session_list)} recent sessions")

                return jsonify(result)
        except Exception as e:
            logger.error(f"Error fetching recent sessions: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/sessions/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        """Delete a session and all associated data"""
        try:
            from gcp.database.models import Session, Drawing, Comparison, AnalysisResult
            with get_db_session() as db:
                # First check if session exists
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404

                # Delete associated data (cascading should handle this, but let's be explicit)
                db.query(AnalysisResult).filter_by(session_id=session_id).delete()
                db.query(Comparison).filter_by(session_id=session_id).delete()

                # Get drawing storage paths for cleanup
                drawings = db.query(Drawing).filter_by(session_id=session_id).all()
                storage_paths = [d.storage_path for d in drawings if d.storage_path]

                # Delete drawings
                db.query(Drawing).filter_by(session_id=session_id).delete()

                # Delete the session
                db.delete(session)
                db.commit()

                # Clean up storage files if storage service is available
                try:
                    for storage_path in storage_paths:
                        if storage_path and hasattr(storage_service, 'delete_file'):
                            try:
                                storage_service.delete_file(storage_path)
                                logger.info(f"Deleted storage file: {storage_path}")
                            except Exception as storage_error:
                                logger.warning(f"Failed to delete storage file {storage_path}: {storage_error}")
                except Exception as cleanup_error:
                    logger.warning(f"Storage cleanup failed: {cleanup_error}")

                # Clear cache after successful deletion
                recent_sessions_cache.clear('recent_sessions')

                logger.info(f"Session {session_id} deleted successfully")
                return jsonify({
                    'success': True,
                    'message': 'Session deleted successfully',
                    'session_id': session_id
                })

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return jsonify({'error': str(e)}), 500

# Chat functionality
@app.route('/api/chat/<session_id>', methods=['POST'])
def chat_message(session_id):
    """Handle chatbot messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        if config.USE_DATABASE:
            # TODO: Use database chat storage
            pass
        else:
            # Use in-memory storage for local mode
            if session_id not in conversation_histories:
                conversation_histories[session_id] = []

            user_chat_msg = ChatMessage(
                role="user",
                content=user_message,
                timestamp=datetime.now(timezone.utc),
                session_id=session_id
            )
            conversation_histories[session_id].append(user_chat_msg)

        response_msg = chatbot.chat(
            user_message=user_message,
            session_id=session_id,
            conversation_history=conversation_histories.get(session_id, []) if not config.USE_DATABASE else []
        )

        if not config.USE_DATABASE:
            conversation_histories[session_id].append(response_msg)
            if len(conversation_histories[session_id]) > 20:
                conversation_histories[session_id] = conversation_histories[session_id][-20:]

        return jsonify({
            'response': response_msg.content,
            'timestamp': response_msg.timestamp.isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/suggested', methods=['GET'])
def get_suggested_questions(session_id):
    """Get suggested questions for the chatbot"""
    try:
        suggestions = chatbot.get_suggested_questions(session_id)
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a session"""
    try:
        if config.USE_DATABASE:
            # TODO: Use database chat history
            history = []
        else:
            history = conversation_histories.get(session_id, [])
            history = [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in history
            ]

        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/diagnostics')
def get_session_diagnostics(session_id):
    """Get detailed diagnostics for a processing session to identify issues"""
    try:
        diagnostics = {
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'issues_detected': [],
            'recommendations': []
        }

        if config.USE_DATABASE:
            from gcp.database.models import Session, Drawing, Comparison, AnalysisResult, ProcessingJob

            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404

                # Basic session info
                diagnostics['session'] = {
                    'status': session.status,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                    'metadata': session.session_metadata or {}
                }

                # Calculate processing time
                now = datetime.utcnow()
                time_since_created = now - session.created_at.replace(tzinfo=None)
                time_since_updated = now - session.updated_at.replace(tzinfo=None)

                diagnostics['processing_time'] = {
                    'hours_since_created': round(time_since_created.total_seconds() / 3600, 2),
                    'minutes_since_updated': round(time_since_updated.total_seconds() / 60, 2)
                }

                # Check database records
                drawings_count = db.query(Drawing).filter_by(session_id=session_id).count()
                comparisons_count = db.query(Comparison).filter_by(session_id=session_id).count()
                analyses_count = db.query(AnalysisResult).filter_by(session_id=session_id).count()

                diagnostics['records'] = {
                    'drawings': drawings_count,
                    'comparisons': comparisons_count,
                    'analyses': analyses_count
                }

                # Get processing jobs info
                jobs = db.query(ProcessingJob).filter_by(session_id=session_id).all()
                diagnostics['processing_jobs'] = []
                for job in jobs:
                    job_info = {
                        'type': job.job_type,
                        'status': job.status,
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'error': job.error_message
                    }
                    diagnostics['processing_jobs'].append(job_info)

                # Identify issues
                if session.status == 'processing':
                    # Check for timeout conditions
                    metadata = session.session_metadata or {}
                    pages_count = metadata.get('pages_count', 0)

                    if time_since_updated.total_seconds() / 60 > 60:
                        diagnostics['issues_detected'].append({
                            'type': 'stale_processing',
                            'severity': 'high',
                            'message': f'No updates for {time_since_updated.total_seconds() / 60:.0f} minutes'
                        })

                    if drawings_count == 0:
                        diagnostics['issues_detected'].append({
                            'type': 'no_drawings',
                            'severity': 'critical',
                            'message': 'No drawings uploaded - upload may have failed'
                        })
                        diagnostics['recommendations'].append('Retry upload with fresh session')

                    if drawings_count > 0 and comparisons_count == 0:
                        diagnostics['issues_detected'].append({
                            'type': 'comparison_failure',
                            'severity': 'high',
                            'message': 'Drawings uploaded but no comparisons created'
                        })
                        diagnostics['recommendations'].append('Check drawing alignment algorithm')

                    if comparisons_count > 0 and analyses_count == 0:
                        diagnostics['issues_detected'].append({
                            'type': 'ai_analysis_failure',
                            'severity': 'medium',
                            'message': 'Comparisons created but AI analysis failed'
                        })
                        diagnostics['recommendations'].append('Check OpenAI API credentials and connectivity')

                    # Check for database connection issues
                    if any(job.error_message and 'connection' in job.error_message.lower()
                           for job in jobs if job.error_message):
                        diagnostics['issues_detected'].append({
                            'type': 'database_connection',
                            'severity': 'critical',
                            'message': 'Database connection errors detected'
                        })
                        diagnostics['recommendations'].append('Check Cloud SQL Proxy and authentication')

                    # Check for GCS issues
                    if any(job.error_message and ('storage' in job.error_message.lower() or
                                                   'gcs' in job.error_message.lower())
                           for job in jobs if job.error_message):
                        diagnostics['issues_detected'].append({
                            'type': 'storage_failure',
                            'severity': 'critical',
                            'message': 'Google Cloud Storage access issues'
                        })
                        diagnostics['recommendations'].append('Run: gcloud auth application-default login')

                # Overall health assessment
                if len(diagnostics['issues_detected']) == 0:
                    diagnostics['health'] = 'healthy'
                    diagnostics['message'] = 'Session processing normally'
                elif any(issue['severity'] == 'critical' for issue in diagnostics['issues_detected']):
                    diagnostics['health'] = 'critical'
                    diagnostics['message'] = 'Critical issues preventing processing'
                elif any(issue['severity'] == 'high' for issue in diagnostics['issues_detected']):
                    diagnostics['health'] = 'unhealthy'
                    diagnostics['message'] = 'Session likely stuck or failing'
                else:
                    diagnostics['health'] = 'degraded'
                    diagnostics['message'] = 'Minor issues detected'

        return jsonify(diagnostics)

    except Exception as e:
        logger.error(f"Diagnostics error for session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/debug-context', methods=['GET'])
def debug_chatbot_context(session_id):
    """Debug endpoint to check chatbot context retrieval"""
    try:
        # Get the context that the chatbot would use
        context = chatbot.get_session_context(session_id)

        return jsonify({
            'session_id': session_id,
            'context': context,
            'config_use_database': config.USE_DATABASE,
            'overlays_created': context.get('overlays_created', 0),
            'analyses_completed': context.get('analyses_completed', 0),
            'changes_count': len(context.get('changes', [])),
            'drawings': context.get('drawings', [])
        })
    except Exception as e:
        logger.error(f"Debug context error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-task', methods=['POST'])
def process_task():
    """Process drawing comparison task (called by Cloud Tasks)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        session_id = data.get('session_id')
        old_path = data.get('old_path')
        new_path = data.get('new_path')
        old_name = data.get('old_name')
        new_name = data.get('new_name')

        if not all([session_id, old_path, new_path, old_name, new_name]):
            return jsonify({'error': 'Missing required parameters'}), 400

        logger.info(f"Processing task for session {session_id}")

        # Update session status to processing
        if config.USE_DATABASE:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if session:
                    session.status = 'processing'
                    session.updated_at = datetime.utcnow()
                    if not session.session_metadata:
                        session.session_metadata = {}
                    session.session_metadata['current_step'] = 'task_processing'
                    session.session_metadata['processing_started'] = datetime.utcnow().isoformat()
                    db.commit()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Download files to temp directory
            old_temp_path = os.path.join(temp_dir, old_name)
            new_temp_path = os.path.join(temp_dir, new_name)

            if not storage_service.download_to_filename(old_path, old_temp_path):
                raise Exception("Failed to download old file")

            if not storage_service.download_to_filename(new_path, new_temp_path):
                raise Exception("Failed to download new file")

            # Use chunked processor for large files to get proper statistics
            results = chunked_process_documents(
                old_pdf_path=old_temp_path,
                new_pdf_path=new_temp_path,
                session_id=session_id
            )

            # Store results
            if results['success']:
                # Update session with results
                if config.USE_DATABASE:
                    _store_results_to_database(session_id, results, old_path, new_path)

                # Update session status and metadata to completed
                with get_db_session() as db:
                    session = db.query(Session).filter_by(id=session_id).first()
                    if session:
                        session.status = 'completed'
                        session.total_time = results['summary']['total_time']
                        # Serialize results to handle ChangeAnalysisResult objects
                        serialized_results = serialize_results_for_json(results)
                        # Store results in session_metadata for results page
                        session.session_metadata = {'results': serialized_results}
                        session.updated_at = datetime.utcnow()
                        db.commit()

                logger.info(f"Task processing completed for session {session_id}")
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'message': 'Processing completed successfully'
                })
            else:
                raise Exception(results.get('error', 'Processing failed'))

    except Exception as e:
        logger.error(f"Task processing failed for session {session_id}: {e}")
        # Update session status to error
        if config.USE_DATABASE:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if session:
                    session.status = 'error'
                    session.session_metadata = {'error': str(e)}
                    session.updated_at = datetime.utcnow()
                    db.commit()

        return jsonify({'error': str(e)}), 500


@app.route('/api/retry-task', methods=['POST'])
def retry_task():
    """Retry processing for a failed session (called by Cloud Tasks)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        session_id = data.get('session_id')
        retry_attempt = data.get('retry_attempt', 1)

        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400

        logger.info(f"Retrying task for session {session_id}, attempt {retry_attempt}")

        if config.USE_DATABASE:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if not session:
                    return jsonify({'error': 'Session not found'}), 404

                # Get original file paths from drawings
                drawings = db.query(Drawing).filter_by(session_id=session_id).all()
                if len(drawings) < 2:
                    return jsonify({'error': 'Original files not found'}), 404

                old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
                new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

                if not old_drawing or not new_drawing:
                    return jsonify({'error': 'Original drawing files not found'}), 404

                # Create a new processing task
                from gcp.tasks import task_processor
                task_name = task_processor.create_processing_task(
                    session_id=session_id,
                    old_path=old_drawing.storage_path,
                    new_path=new_drawing.storage_path,
                    old_name=old_drawing.filename,
                    new_name=new_drawing.filename
                )

                # Update session status
                session.status = 'processing'
                session.updated_at = datetime.utcnow()
                if not session.session_metadata:
                    session.session_metadata = {}
                session.session_metadata['retry_attempt'] = retry_attempt
                session.session_metadata['retry_task'] = task_name
                db.commit()

                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'task_name': task_name,
                    'message': f'Retry task created, attempt {retry_attempt}'
                })

        return jsonify({'error': 'Database not available'}), 500

    except Exception as e:
        logger.error(f"Retry task failed for session {session_id}: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info(f"Starting BuildTrace on {config.HOST}:{config.PORT}")
    logger.info(f"Configuration: {config}")

    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT
    )