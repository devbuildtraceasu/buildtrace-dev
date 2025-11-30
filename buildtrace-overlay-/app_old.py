#!/usr/bin/env python3
"""
BuildTrace AI Web Application - Updated with Database and Cloud Storage

Flask web app with PostgreSQL database and Cloud Storage integration.
Supports project-based organization and automatic version tracking.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

# Load environment variables (only in development)
from dotenv import load_dotenv
if os.getenv('ENVIRONMENT') != 'production':
    load_dotenv()

# Import database and services
from database import get_db_session
from services.project_service import ProjectService
from services.storage_service import storage_service
from models import User, Project, Session, Drawing, Comparison, AnalysisResult, ChatConversation, ChatMessage as DBChatMessage

# Import existing pipeline functions
from complete_drawing_pipeline import complete_drawing_pipeline

def store_processing_results(session_id, results, db):
    """Store processing results in the database"""
    try:
        print(f"📊 Storing results for session {session_id}")
        print(f"   Results keys: {results.keys()}")

        # Get session and drawings
        session = db.query(Session).filter_by(id=session_id).first()
        if not session:
            raise Exception(f"Session {session_id} not found")

        drawings = db.query(Drawing).filter_by(session_id=session_id).all()
        old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
        new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

        if not old_drawing or not new_drawing:
            raise Exception("Required drawings not found")

        # Process comparison results
        comparisons = results.get('comparisons', [])
        print(f"   Found {len(comparisons)} comparisons to store")
        analysis_results = results.get('analysis_results', [])

        for i, comparison_data in enumerate(comparisons):
            if not comparison_data.get('success', False):
                print(f"   ❌ Skipping failed comparison {i}")
                continue

            drawing_name = comparison_data.get('drawing_name', f'Drawing {i+1}')
            print(f"   📄 Processing comparison for: {drawing_name}")
            print(f"      - Overlay path: {comparison_data.get('overlay_path', 'None')}")
            print(f"      - Old image path: {comparison_data.get('old_image_path', 'None')}")
            print(f"      - New image path: {comparison_data.get('new_image_path', 'None')}")

            # Check if comparison already exists
            existing_comparison = db.query(Comparison).filter_by(
                session_id=session_id,
                drawing_name=drawing_name
            ).first()

            if existing_comparison:
                continue  # Skip if already exists

            # Create comparison record
            comparison = Comparison(
                session_id=session_id,
                old_drawing_id=old_drawing.id,
                new_drawing_id=new_drawing.id,
                drawing_name=drawing_name,
                overlay_path=comparison_data.get('overlay_path'),
                old_image_path=comparison_data.get('old_image_path'),
                new_image_path=comparison_data.get('new_image_path'),
                alignment_score=comparison_data.get('alignment_score', 0.0),
                changes_detected=comparison_data.get('changes_detected', False)
            )
            db.add(comparison)
            db.flush()  # Get the ID

            # Add analysis result if available
            if i < len(analysis_results):
                analysis_data = analysis_results[i]
                if isinstance(analysis_data, dict):
                    # Parse changes_found if it's a string
                    changes_found = analysis_data.get('changes_found', [])
                    if isinstance(changes_found, str):
                        # Try to extract bullet points from summary
                        changes_found = [line.strip('- •') for line in changes_found.split('\n') if line.strip().startswith(('-', '•'))]

                    analysis_result = AnalysisResult(
                        comparison_id=comparison.id,
                        drawing_name=drawing_name,
                        critical_change=analysis_data.get('critical_change', ''),
                        analysis_summary=analysis_data.get('analysis_summary', comparison_data.get('analysis', '')),
                        changes_found=changes_found if changes_found else None,
                        recommendations=analysis_data.get('recommendations', None),
                        success=analysis_data.get('success', True)
                    )
                    db.add(analysis_result)
            else:
                # No AI analysis available, create basic result from comparison
                analysis_result = AnalysisResult(
                    comparison_id=comparison.id,
                    drawing_name=drawing_name,
                    critical_change='Changes detected' if comparison_data.get('changes_detected') else 'No changes detected',
                    analysis_summary=comparison_data.get('analysis', f"Comparison completed for {drawing_name}"),
                    changes_found=None,
                    recommendations=None,
                    success=True
                )
                db.add(analysis_result)

        db.commit()
        print(f"✅ Stored {len(comparisons)} comparison results in database")

    except Exception as e:
        print(f"❌ Error storing processing results: {e}")
        db.rollback()
        raise
from chatbot_service import ConstructionChatBot, ChatMessage

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File handling
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'png', 'jpg', 'jpeg'}

# Initialize chatbot
chatbot = ConstructionChatBot()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_or_create_user(email=None):
    """Get or create a user for the session"""
    with get_db_session() as db:
        project_service = ProjectService(db)
        return project_service.get_or_create_user(email)

@app.route('/')
def index():
    """Main upload interface"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads with database and cloud storage"""
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
            return jsonify({'error': 'Invalid file type. Allowed: PDF, DWG, DXF, PNG, JPG'}), 400

        # Get optional parameters
        user_email = request.form.get('user_email')
        project_id = request.form.get('project_id')

        with get_db_session() as db:
            project_service = ProjectService(db)

            # Get or create user
            user = project_service.get_or_create_user(user_email)

            # Get or create project
            if project_id:
                project = db.query(Project).filter_by(id=project_id, user_id=user.id).first()
                if not project:
                    return jsonify({'error': 'Project not found'}), 404
            else:
                project = project_service.get_or_create_default_project(user.id)

            # Create new session
            session = Session(
                user_id=user.id,
                project_id=project.id,
                session_type='comparison',
                status='uploading'
            )
            db.add(session)
            db.commit()

            session_id = session.id

            # Upload files to cloud storage
            old_filename = secure_filename(old_file.filename)
            new_filename = secure_filename(new_file.filename)

            # Store files in cloud storage
            old_storage_path = f"sessions/{session_id}/old_{old_filename}"
            new_storage_path = f"sessions/{session_id}/new_{new_filename}"

            storage_service.upload_file(
                old_file.stream,
                old_storage_path,
                content_type=old_file.content_type
            )
            storage_service.upload_file(
                new_file.stream,
                new_storage_path,
                content_type=new_file.content_type
            )

            # Create drawing records
            old_drawing = Drawing(
                session_id=session_id,
                drawing_type='old',
                filename=f"old_{old_filename}",
                original_filename=old_filename,
                storage_path=old_storage_path
            )
            new_drawing = Drawing(
                session_id=session_id,
                drawing_type='new',
                filename=f"new_{new_filename}",
                original_filename=new_filename,
                storage_path=new_storage_path
            )

            db.add(old_drawing)
            db.add(new_drawing)
            db.commit()

            # Update session status
            session.status = 'uploaded'
            db.commit()

            return jsonify({
                'session_id': session_id,
                'project_id': project.id,
                'project_name': project.name,
                'old_filename': old_filename,
                'new_filename': new_filename,
                'user_id': user.id
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process/<session_id>', methods=['POST'])
def process_drawings(session_id):
    """Smart processing: sync for small docs, async for large docs"""
    try:
        with get_db_session() as db:
            # Get session and drawings
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404

            drawings = db.query(Drawing).filter_by(session_id=session_id).all()
            old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
            new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

            if not old_drawing or not new_drawing:
                return jsonify({'error': 'Drawings not found'}), 404

            # Download files to check size
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                old_temp_path = os.path.join(temp_dir, old_drawing.filename)
                new_temp_path = os.path.join(temp_dir, new_drawing.filename)

                # Download files
                storage_service.download_to_filename(old_drawing.storage_path, old_temp_path)
                storage_service.download_to_filename(new_drawing.storage_path, new_temp_path)

                # Use chunked processor to decide sync vs async
                from chunked_processor import ChunkedProcessor
                # Reduce threshold for cloud environment to handle memory constraints
                max_pages = 3 if os.getenv('ENVIRONMENT') == 'production' else 10
                processor = ChunkedProcessor(max_sync_pages=max_pages)

                if processor.should_process_sync(old_temp_path, new_temp_path):
                    # Process immediately with page-by-page approach
                    session.status = 'processing'
                    db.commit()

                    # Import the function from chunked_processor
                    from chunked_processor import process_documents
                    results = process_documents(old_temp_path, new_temp_path, session_id)

                    if results['success']:
                        # Results are now automatically saved to database by ChunkedProcessor
                        session.status = 'completed'
                        session.total_time = results.get('summary', {}).get('processing_time', 0.0)
                        db.commit()

                        return jsonify({
                            'success': True,
                            'processing_type': 'immediate',
                            'session_id': session_id,
                            'pages_processed': results.get('pages_processed', 0),
                            'total_comparisons': len(results.get('comparisons', [])),
                            'processing_time': results.get('summary', {}).get('processing_time', 0.0),
                            'overlays_created': len(results.get('comparisons', [])),
                            'message': 'Small document processed immediately with page-by-page method'
                        })
                    else:
                        session.status = 'error'
                        db.commit()
                        return jsonify({
                            'success': False,
                            'error': results.get('error', 'Processing failed')
                        }), 500

                else:
                    # Large document - use background job system
                    from models import ProcessingJob
                    job = ProcessingJob(
                        session_id=session_id,
                        job_type='drawing_comparison',
                        status='pending'
                    )
                    db.add(job)

                    session.status = 'queued'
                    db.commit()

                    return jsonify({
                        'success': True,
                        'processing_type': 'background',
                        'message': 'Large document queued for background processing',
                        'job_id': job.id,
                        'session_id': session_id,
                        'status': 'queued',
                        'note': 'Check /status/<session_id> for progress updates'
                    })

    except Exception as e:
        # Update session status on error
        try:
            with get_db_session() as db:
                session = db.query(Session).filter_by(id=session_id).first()
                if session:
                    session.status = 'error'
                    db.commit()
        except Exception:
            pass

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/status/<session_id>')
def check_processing_status(session_id):
    """Check the status of background processing job"""
    try:
        with get_db_session() as db:
            from models import ProcessingJob

            # Get the latest job for this session
            job = db.query(ProcessingJob).filter_by(
                session_id=session_id
            ).order_by(ProcessingJob.created_at.desc()).first()

            if not job:
                return jsonify({'error': 'No job found for this session'}), 404

            # Get session info
            session = db.query(Session).filter_by(id=session_id).first()

            return jsonify({
                'job_id': job.id,
                'session_id': session_id,
                'status': job.status,
                'session_status': session.status if session else 'unknown',
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'result': job.result,
                'error_message': job.error_message
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results/<session_id>')
def view_results(session_id):
    """Display results page with database integration"""
    try:
        with get_db_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return "Session not found", 404

            # Get analysis results from database
            comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
            analysis_results = []

            for comparison in comparisons:
                results = db.query(AnalysisResult).filter_by(comparison_id=comparison.id).all()
                for result in results:
                    analysis_results.append({
                        'drawing_name': result.drawing_name,
                        'changes_found': result.changes_found or [],
                        'critical_change': result.critical_change,
                        'analysis_summary': result.analysis_summary,
                        'recommendations': result.recommendations or [],
                        'success': result.success
                    })

            # Build results structure for template compatibility
            results_data = {
                'success': session.status == 'completed',
                'analysis_results': analysis_results,
                'summary': {
                    'overlays_created': len(comparisons),
                    'analyses_completed': len(analysis_results),
                    'total_time': session.total_time or 0
                }
            }

            return render_template('results.html',
                                 session_id=session_id,
                                 results=results_data)

    except Exception as e:
        return f"Error loading results: {str(e)}", 500

@app.route('/api/changes/<session_id>')
def get_changes(session_id):
    """API endpoint to get changes data from database"""
    try:
        with get_db_session() as db:
            # Get analysis results from database
            comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
            changes = []

            for i, comparison in enumerate(comparisons):
                analysis_results = db.query(AnalysisResult).filter_by(comparison_id=comparison.id).all()

                for result in analysis_results:
                    changes.append({
                        'id': i + 1,
                        'drawing_number': result.drawing_name,
                        'description': result.critical_change or 'Changes detected',
                        'details': result.changes_found or [],
                        'summary': result.analysis_summary or f"Analysis completed for {result.drawing_name}",
                        'recommendations': result.recommendations or [
                            'Review structural implications',
                            'Update cost estimates',
                            'Revise construction schedule',
                            'Check permit requirements'
                        ]
                    })

            return jsonify({'changes': changes})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drawings/<session_id>')
def get_drawing_images(session_id):
    """Get available drawing images from storage (cloud or local)"""
    try:
        print(f"🔍 Getting drawings for session: {session_id}")

        with get_db_session() as db:
            comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
            print(f"   Found {len(comparisons)} comparisons in database")

            drawing_comparisons = []

            for i, comparison in enumerate(comparisons):
                print(f"   Processing comparison {i+1}: {comparison.drawing_name}")
                print(f"      Overlay path: {comparison.overlay_path}")
                print(f"      Old path: {comparison.old_image_path}")
                print(f"      New path: {comparison.new_image_path}")
                
                # Generate URLs for each image type
                overlay_url = _get_image_url(comparison.overlay_path, session_id, comparison.drawing_name, 'overlay')
                old_url = _get_image_url(comparison.old_image_path, session_id, comparison.drawing_name, 'old')
                new_url = _get_image_url(comparison.new_image_path, session_id, comparison.drawing_name, 'new')

                print(f"      Final URLs - Overlay: {bool(overlay_url)}, Old: {bool(old_url)}, New: {bool(new_url)}")

                if overlay_url:  # Only include if overlay exists
                    comparison_data = {
                        'drawing_name': comparison.drawing_name,
                        'old_image': old_url,
                        'new_image': new_url,
                        'overlay_image': overlay_url
                    }
                    drawing_comparisons.append(comparison_data)
                    print(f"      ✅ Added comparison: {comparison.drawing_name}")
                else:
                    print(f"      ❌ Skipped comparison {comparison.drawing_name}: No overlay URL")

            print(f"   Returning {len(drawing_comparisons)} comparisons")
            return jsonify({'comparisons': drawing_comparisons})

    except Exception as e:
        print(f"❌ Error in get_drawing_images: {str(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


def _get_image_url(image_path, session_id, drawing_name, image_type):
    """
    Smart image URL generation that handles both local and cloud storage.
    
    Args:
        image_path: Path stored in database (could be local or GCS path)
        session_id: Session ID for local file serving
        drawing_name: Drawing name for local file serving
        image_type: Type of image (overlay, old, new) for logging
    
    Returns:
        URL string or None if image not available
    """
    if not image_path:
        return None
    
    try:
        # Check if this is a GCS path (starts with gs:// or contains bucket name)
        is_gcs_path = (
            image_path.startswith('gs://') or 
            'buildtrace-storage' in image_path or
            image_path.startswith('sessions/')
        )
        
        # Check if cloud storage is available
        cloud_storage_available = (
            hasattr(storage_service, 'bucket') and 
            storage_service.bucket is not None
        )
        
        print(f"      {image_type}: {image_path[:50]}...")
        print(f"      {image_type}: Is GCS path: {is_gcs_path}")
        print(f"      {image_type}: Cloud storage available: {cloud_storage_available}")
        
        # Strategy 1: If it's a GCS path and cloud storage is available, use signed URL
        if is_gcs_path and cloud_storage_available:
            try:
                url = storage_service.generate_signed_url(image_path, 60)
                print(f"      {image_type}: Generated cloud URL: {url[:50]}...")
                return url
            except Exception as e:
                print(f"      {image_type}: Cloud URL generation failed: {e}")
                # Fall through to local serving
        
        # Strategy 2: If it's a local path or cloud storage unavailable, use local serving
        if not is_gcs_path or not cloud_storage_available:
            filename = os.path.basename(image_path)
            url = f"/api/files/{session_id}/{drawing_name}/{filename}"
            print(f"      {image_type}: Using local URL: {url}")
            return url
        
        # Strategy 3: If GCS path but no cloud storage, try to serve locally
        # This handles the case where DB has GCS paths but we're running locally
        if is_gcs_path and not cloud_storage_available:
            filename = os.path.basename(image_path)
            url = f"/api/files/{session_id}/{drawing_name}/{filename}"
            print(f"      {image_type}: GCS path but no cloud storage, trying local: {url}")
            return url
            
    except Exception as e:
        print(f"      {image_type}: Error generating URL: {e}")
        return None
    
    return None

@app.route('/api/debug/session/<session_id>')
def debug_session(session_id):
    """Debug endpoint to check what's stored for a session"""
    try:
        with get_db_session() as db:
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404

            comparisons = db.query(Comparison).filter_by(session_id=session_id).all()

            debug_info = {
                'session': {
                    'id': session.id,
                    'status': session.status,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'total_time': session.total_time
                },
                'comparisons': []
            }

            for comp in comparisons:
                debug_info['comparisons'].append({
                    'drawing_name': comp.drawing_name,
                    'overlay_path': comp.overlay_path,
                    'old_image_path': comp.old_image_path,
                    'new_image_path': comp.new_image_path,
                    'has_overlay': bool(comp.overlay_path),
                    'has_old': bool(comp.old_image_path),
                    'has_new': bool(comp.new_image_path)
                })

            return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/recent')
def get_recent_sessions():
    """Get recent comparison sessions for display on home page"""
    try:
        with get_db_session() as db:
            # Get recent completed sessions (limit to last 10)
            sessions = db.query(Session).filter(
                Session.status == 'completed'
            ).order_by(Session.created_at.desc()).limit(10).all()

            session_list = []
            for session in sessions:
                # Get drawing count for this session
                comparisons = db.query(Comparison).filter_by(session_id=session.id).all()

                # Get project name if available
                project_name = session.project.name if session.project else "Untitled Project"

                session_list.append({
                    'id': session.id,
                    'project_name': project_name,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'total_time': session.total_time or 0,
                    'comparison_count': len(comparisons),
                    'status': session.status
                })

            return jsonify({'sessions': session_list})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/suggested')
def get_suggested_questions(session_id):
    """Get suggested questions based on analysis results"""
    try:
        with get_db_session() as db:
            # Get analysis results to generate relevant questions
            comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
            suggestions = [
                "What are the cost implications of these changes?",
                "How will these changes affect the project timeline?",
                "What permits might be required for these modifications?",
                "Are there any structural concerns with these changes?",
                "What materials will be needed for these modifications?"
            ]

            # Add drawing-specific questions if we have results
            if comparisons:
                for comparison in comparisons[:2]:  # Limit to first 2 drawings
                    suggestions.append(f"Tell me more about the changes in {comparison.drawing_name}")

            return jsonify({'suggestions': suggestions[:6]})  # Limit to 6 suggestions
    except Exception as e:
        return jsonify({'suggestions': [
            "What are the cost implications of these changes?",
            "How will these changes affect the project timeline?"
        ]}), 200  # Return default suggestions even if DB fails

@app.route('/api/files/<session_id>/<drawing_name>/<filename>')
def serve_local_file(session_id, drawing_name, filename):
    """Serve local files for development when cloud storage is not available"""
    try:
        print(f"🔍 Looking for file: {filename} for session {session_id}, drawing {drawing_name}")
        
        # Look for the file in the local uploads directory
        # Check different possible paths based on the pipeline output structure
        possible_paths = [
            # Standard pipeline output structure
            f"uploads/sessions/{session_id}/results/{drawing_name}/{filename}",
            f"uploads/sessions/{session_id}/{drawing_name}_overlay_results/{filename}",
            f"uploads/{session_id}/{drawing_name}_overlay_results/{filename}",
            
            # Alternative structures
            f"uploads/{session_id}/results/{drawing_name}/{filename}",
            f"uploads/{session_id}/{drawing_name}/{filename}",
            
            # Direct file locations
            f"uploads/{filename}",
            f"drawings/{filename}",
            f"new_{drawing_name}_overlays/{drawing_name}_overlay_results/{filename}",
            f"new_{drawing_name}_overlays/{filename}",
            
            # Fallback to current directory
            filename,
        ]

        for file_path in possible_paths:
            if os.path.exists(file_path):
                from flask import send_file
                print(f"✅ Serving file: {file_path}")
                return send_file(file_path, mimetype='image/png')

        # If not found, log and return a 404
        print(f"❌ File not found. Looked in: {possible_paths}")
        return "File not found", 404

    except Exception as e:
        print(f"❌ Error serving file: {e}")
        return f"Error serving file: {str(e)}", 500

@app.route('/api/chat/<session_id>', methods=['POST'])
def chat_message(session_id):
    """Handle chatbot messages with database storage"""
    try:
        logger.info(f"Chat endpoint called for session {session_id}")
        data = request.get_json()
        logger.info(f"Request data: {data}")
        user_message = data.get('message', '').strip()
        logger.info(f"User message: {user_message}")

        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        try:
            with get_db_session() as db:
                # Get or create conversation
                conversation = db.query(ChatConversation).filter_by(session_id=session_id).first()
                if not conversation:
                    conversation = ChatConversation(session_id=session_id)
                    db.add(conversation)
                    db.commit()

                # Add user message to database
                user_db_msg = DBChatMessage(
                    conversation_id=conversation.id,
                    role="user",
                    content=user_message
                )
                db.add(user_db_msg)
                db.commit()

                # Get conversation history from database
                history_msgs = db.query(DBChatMessage).filter_by(
                    conversation_id=conversation.id
                ).order_by(DBChatMessage.timestamp.desc()).limit(20).all()

                # Get analysis results for context
                comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
                analysis_context = []
                for comparison in comparisons:
                    results = db.query(AnalysisResult).filter_by(comparison_id=comparison.id).all()
                    for result in results:
                        analysis_context.append({
                            'drawing_name': result.drawing_name,
                            'critical_change': result.critical_change,
                            'analysis_summary': result.analysis_summary,
                            'changes_found': result.changes_found,
                            'recommendations': result.recommendations
                        })

                use_db = True
        except Exception as db_error:
            logger.warning(f"Database unavailable for chat: {db_error}, proceeding without database")
            history_msgs = []
            analysis_context = []
            use_db = False

            # Convert to chatbot format
            conversation_history = [
                ChatMessage(
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    session_id=session_id
                ) for msg in reversed(history_msgs)
            ]

            # Generate response with analysis context
            logger.info(f"Calling chatbot.chat with message: {user_message}")
            logger.info(f"Analysis context count: {len(analysis_context)}")

            # Create a temporary system message with analysis context for this session
            if analysis_context:
                context_msg = ChatMessage(
                    role='system',
                    content=f"Current session analysis results: {json.dumps(analysis_context, indent=2)}",
                    timestamp=datetime.now(),
                    session_id=session_id
                )
                # Add context at the beginning of conversation history
                enhanced_history = [context_msg] + (conversation_history or [])
            else:
                enhanced_history = conversation_history

            response_msg = chatbot.chat(
                user_message=user_message,
                session_id=session_id,
                conversation_history=enhanced_history
            )

            logger.info(f"Chatbot response: {response_msg.content}")

            # Save assistant response to database if available
            if use_db:
                try:
                    with get_db_session() as db:
                        assistant_db_msg = DBChatMessage(
                            conversation_id=conversation.id,
                            role="assistant",
                            content=response_msg.content
                        )
                        db.add(assistant_db_msg)
                        db.commit()
                except Exception as save_error:
                    logger.warning(f"Could not save response to database: {save_error}")

            return jsonify({
                'response': response_msg.content,
                'timestamp': response_msg.timestamp.isoformat()
            })

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history from database"""
    try:
        with get_db_session() as db:
            conversation = db.query(ChatConversation).filter_by(session_id=session_id).first()
            if not conversation:
                return jsonify({'history': []})

            messages = db.query(DBChatMessage).filter_by(
                conversation_id=conversation.id
            ).order_by(DBChatMessage.timestamp).all()

            formatted_history = [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]

            return jsonify({'history': formatted_history})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get projects for a user"""
    try:
        user_email = request.args.get('user_email')

        with get_db_session() as db:
            project_service = ProjectService(db)
            user = project_service.get_or_create_user(user_email)
            projects = project_service.list_user_projects(user.id)

            project_list = [
                {
                    'id': p.id,
                    'name': p.name,
                    'description': p.description,
                    'client_name': p.client_name,
                    'location': p.location,
                    'created_at': p.created_at.isoformat(),
                    'status': p.status
                }
                for p in projects
            ]

            return jsonify({'projects': project_list})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()

        with get_db_session() as db:
            project_service = ProjectService(db)
            user = project_service.get_or_create_user(data.get('user_email'))

            project = project_service.create_project(
                user_id=user.id,
                name=data['name'],
                description=data.get('description'),
                client_name=data.get('client_name'),
                location=data.get('location')
            )

            return jsonify({
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'created_at': project.created_at.isoformat()
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)