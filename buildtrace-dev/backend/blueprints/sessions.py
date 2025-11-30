#!/usr/bin/env python3
"""
Session-based API Endpoints

Provides session-based processing endpoints for backward compatibility
with buildtrace-overlay- while supporting the modern job-based architecture.
"""

import logging
import uuid
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy.orm import Session as DBSession

from config import config
from gcp.database import get_db_session
from gcp.database.models import Session, Drawing, Comparison, AnalysisResult
from gcp.storage.storage_service import StorageService
from services.session_service import SessionService
from services.drawing_service import DrawingUploadService
from utils.auth_helpers import get_current_user_id, require_auth
from utils.local_output_manager import get_output_manager

logger = logging.getLogger(__name__)

sessions_bp = Blueprint('sessions', __name__, url_prefix='/api/v1/sessions')

# Initialize services
storage_service = StorageService()
drawing_service = DrawingUploadService()


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@sessions_bp.route('/upload', methods=['POST'])
@require_auth
def upload_files():
    """
    Upload old and new drawing files and create a session
    
    Request:
        - old_file: File upload (multipart/form-data)
        - new_file: File upload (multipart/form-data)
        - project_id: Optional project ID
    
    Returns:
        - session_id: Created session ID
        - status: Upload status
    """
    try:
        user_id = get_current_user_id()
        
        # Check for files
        if 'old_file' not in request.files or 'new_file' not in request.files:
            return jsonify({'error': 'Both old_file and new_file are required'}), 400
        
        old_file = request.files['old_file']
        new_file = request.files['new_file']
        
        if old_file.filename == '' or new_file.filename == '':
            return jsonify({'error': 'Both files must have filenames'}), 400
        
        if not allowed_file(old_file.filename) or not allowed_file(new_file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Get optional project_id
        project_id = request.form.get('project_id')
        
        # Create session
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.create_session(
                user_id=user_id,
                project_id=project_id,
                session_type='comparison',
                metadata={
                    'old_filename': old_file.filename,
                    'new_filename': new_file.filename
                }
            )
            session_id = session.id
            
            # Save files
            old_drawing = Drawing(
                id=str(uuid.uuid4()),
                session_id=session_id,
                drawing_type='old',
                filename=secure_filename(old_file.filename),
                original_filename=old_file.filename,
                storage_path=f"sessions/{session_id}/old_{secure_filename(old_file.filename)}"
            )
            
            new_drawing = Drawing(
                id=str(uuid.uuid4()),
                session_id=session_id,
                drawing_type='new',
                filename=secure_filename(new_file.filename),
                original_filename=new_file.filename,
                storage_path=f"sessions/{session_id}/new_{secure_filename(new_file.filename)}"
            )
            
            # Upload to storage
            old_file.seek(0)
            new_file.seek(0)
            
            old_content = old_file.read()
            new_content = new_file.read()
            
            storage_service.upload_file(old_content, old_drawing.storage_path)
            storage_service.upload_file(new_content, new_drawing.storage_path)
            
            # Save locally in dev mode
            if config.IS_DEVELOPMENT:
                output_manager = get_output_manager()
                output_manager.save_png(
                    old_drawing.filename,
                    old_content,
                    session_id=session_id,
                    subfolder='uploads'
                )
                output_manager.save_png(
                    new_drawing.filename,
                    new_content,
                    session_id=session_id,
                    subfolder='uploads'
                )
            
            db.add(old_drawing)
            db.add(new_drawing)
            db.commit()
            
            logger.info(f"Created session {session_id} with files uploaded")
            
            return jsonify({
                'session_id': session_id,
                'status': 'uploaded',
                'message': 'Files uploaded successfully'
            }), 201
    
    except Exception as e:
        logger.error(f"Error uploading files: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/process', methods=['POST'])
@require_auth
def process_session(session_id: str):
    """
    Process a session (start comparison pipeline)
    
    This endpoint will be implemented to use the chunked processor
    or convert to a job-based workflow internally.
    
    Args:
        session_id: Session ID
    
    Returns:
        - status: Processing status
        - message: Status message
    """
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # Update status to processing
            session_service.update_session_status(session_id, 'processing')
            
            # TODO: Implement actual processing using chunked_processor
            # For now, return a placeholder response
            return jsonify({
                'session_id': session_id,
                'status': 'processing',
                'message': 'Processing started (implementation pending)'
            }), 202
    
    except Exception as e:
        logger.error(f"Error processing session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/status', methods=['GET'])
def get_session_status(session_id: str):
    """Get session processing status"""
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            return jsonify({
                'session_id': session_id,
                'status': session.status,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'total_time': session.total_time
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting session status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/results', methods=['GET'])
def get_session_results(session_id: str):
    """Get session results (comparisons and analyses)"""
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            comparisons = session_service.get_session_comparisons(session_id)
            analyses = session_service.get_session_analyses(session_id)
            
            # Format results
            results = {
                'session_id': session_id,
                'status': session.status,
                'comparisons': [
                    {
                        'id': comp.id,
                        'drawing_name': comp.drawing_name,
                        'overlay_path': comp.overlay_path,
                        'old_image_path': comp.old_image_path,
                        'new_image_path': comp.new_image_path,
                        'alignment_score': comp.alignment_score,
                        'changes_detected': comp.changes_detected
                    }
                    for comp in comparisons
                ],
                'analyses': [
                    {
                        'id': analysis.id,
                        'drawing_name': analysis.drawing_name,
                        'changes_found': analysis.changes_found,
                        'critical_change': analysis.critical_change,
                        'analysis_summary': analysis.analysis_summary,
                        'recommendations': analysis.recommendations,
                        'success': analysis.success
                    }
                    for analysis in analyses
                ]
            }
            
            return jsonify(results), 200
    
    except Exception as e:
        logger.error(f"Error getting session results: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/summary', methods=['GET'])
def get_session_summary(session_id: str):
    """Get aggregated session summary"""
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            summary = session_service.get_session_summary(session_id)
            return jsonify(summary), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting session summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/changes/all', methods=['GET'])
def get_all_session_changes(session_id: str):
    """Get all changes across all pages in a session"""
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            analyses = session_service.get_session_analyses(session_id)
            
            all_changes = []
            for analysis in analyses:
                if analysis.changes_found:
                    changes_list = analysis.changes_found if isinstance(analysis.changes_found, list) else [analysis.changes_found]
                    for change in changes_list:
                        all_changes.append({
                            'drawing_name': analysis.drawing_name,
                            'change': change,
                            'critical': analysis.critical_change is not None,
                            'analysis_summary': analysis.analysis_summary
                        })
            
            return jsonify({
                'session_id': session_id,
                'total_changes': len(all_changes),
                'changes': all_changes
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting all session changes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/recent', methods=['GET'])
@require_auth
def get_recent_sessions():
    """Get recent sessions for the current user"""
    try:
        user_id = get_current_user_id()
        limit = int(request.args.get('limit', 20))
        
        with get_db_session() as db:
            session_service = SessionService(db)
            sessions = session_service.get_recent_sessions(user_id=user_id, limit=limit)
            
            return jsonify({
                'sessions': [
                    {
                        'id': session.id,
                        'status': session.status,
                        'session_type': session.session_type,
                        'created_at': session.created_at.isoformat() if session.created_at else None,
                        'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                        'total_time': session.total_time
                    }
                    for session in sessions
                ]
            }), 200
    
    except Exception as e:
        logger.error(f"Error getting recent sessions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>', methods=['DELETE'])
@require_auth
def delete_session(session_id: str):
    """Delete a session and all related data"""
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            deleted = session_service.delete_session(session_id)
            
            if not deleted:
                return jsonify({'error': 'Session not found'}), 404
            
            return jsonify({
                'session_id': session_id,
                'message': 'Session deleted successfully'
            }), 200
    
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/debug', methods=['GET'])
@require_auth
def debug_session(session_id: str):
    """Debug endpoint for session information"""
    try:
        with get_db_session() as db:
            session_service = SessionService(db)
            session = session_service.get_session(session_id)
            
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            drawings = session_service.get_session_drawings(session_id)
            comparisons = session_service.get_session_comparisons(session_id)
            analyses = session_service.get_session_analyses(session_id)
            
            return jsonify({
                'session': {
                    'id': session.id,
                    'session_type': session.session_type,
                    'status': session.status,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                    'total_time': session.total_time,
                    'session_metadata': session.session_metadata
                },
                'drawings': [
                    {
                        'id': d.id,
                        'drawing_name': d.drawing_name,
                        'drawing_type': d.drawing_type,
                        'filename': d.filename
                    }
                    for d in drawings
                ],
                'comparisons': [
                    {
                        'id': c.id,
                        'drawing_name': c.drawing_name,
                        'status': 'completed' if c.changes_detected else 'pending'
                    }
                    for c in comparisons
                ],
                'analyses': [
                    {
                        'id': a.id,
                        'drawing_name': a.drawing_name,
                        'critical_change': a.critical_change is not None,
                        'success': a.success
                    }
                    for a in analyses
                ]
            }), 200
    
    except Exception as e:
        logger.error(f"Error debugging session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

