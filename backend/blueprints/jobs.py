"""
Job Management Blueprint
Handles job creation, status queries, and cancellation
"""

from flask import Blueprint, request, jsonify, current_app
from services.orchestrator import OrchestratorService
from datetime import datetime
import logging

# Optional database imports - handle gracefully if not available
try:
    from gcp.database import get_db_session
    from gcp.database.models import Job, JobStage
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Database not available: {e}")

logger = logging.getLogger(__name__)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/v1/jobs')

@jobs_bp.route('', methods=['POST'])
def create_job():
    """Create a new comparison job"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        data = request.get_json()
        old_version_id = data.get('old_drawing_version_id')
        new_drawing_version_id = data.get('new_drawing_version_id')
        project_id = data.get('project_id')
        user_id = data.get('user_id')  # TODO: Get from auth middleware
        
        if not all([old_version_id, new_drawing_version_id, project_id, user_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        orchestrator = OrchestratorService()
        job = orchestrator.create_comparison_job(
            old_version_id=old_version_id,
            new_drawing_version_id=new_drawing_version_id,
            project_id=project_id,
            user_id=user_id
        )
        
        return jsonify({
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat() if job.created_at else None
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating job: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """Get job status"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            return jsonify({
                'job_id': job.id,
                'project_id': job.project_id,
                'status': job.status,
                'old_drawing_version_id': job.old_drawing_version_id,
                'new_drawing_version_id': job.new_drawing_version_id,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting job: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/<job_id>/stages', methods=['GET'])
def get_job_stages(job_id: str):
    """Get stage-level status for a job"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            stages = db.query(JobStage).filter_by(job_id=job_id).all()
            
            stages_data = []
            for stage in stages:
                stages_data.append({
                    'stage_id': stage.id,
                    'stage': stage.stage,
                    'drawing_version_id': stage.drawing_version_id,
                    'status': stage.status,
                    'started_at': stage.started_at.isoformat() if stage.started_at else None,
                    'completed_at': stage.completed_at.isoformat() if stage.completed_at else None,
                    'error_message': stage.error_message,
                    'result_ref': stage.result_ref,
                    'retry_count': stage.retry_count
                })
            
            return jsonify({
                'job_id': job_id,
                'stages': stages_data
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting job stages: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id: str):
    """Cancel a job"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        user_id = request.get_json().get('user_id') if request.is_json else 'system'
        
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job.status in ['completed', 'cancelled']:
                return jsonify({'error': f'Job is already {job.status}'}), 400
            
            job.status = 'cancelled'
            job.cancelled_at = datetime.utcnow()
            job.cancelled_by = user_id
            
            # Cancel all pending stages
            pending_stages = db.query(JobStage).filter_by(
                job_id=job_id,
                status='pending'
            ).all()
            
            for stage in pending_stages:
                stage.status = 'skipped'
            
            db.commit()
            
            return jsonify({
                'job_id': job_id,
                'status': 'cancelled',
                'cancelled_at': job.cancelled_at.isoformat()
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error cancelling job: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/<job_id>/results', methods=['GET'])
def get_job_results(job_id: str):
    """Get complete job results including diff and summary"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            from gcp.database.models import DiffResult, ChangeSummary
            
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            if job.status != 'completed':
                return jsonify({
                    'job_id': job_id,
                    'status': job.status,
                    'message': 'Job not completed yet'
                }), 200
            
            # Get diff result
            diff_result = db.query(DiffResult).filter_by(job_id=job_id).first()
            
            # Get latest summary
            summary = None
            if diff_result:
                summary = db.query(ChangeSummary).filter_by(
                    diff_result_id=diff_result.id,
                    is_active=True
                ).first()
            
            result = {
                'job_id': job_id,
                'status': job.status,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            }
            
            if diff_result:
                result['diff'] = {
                    'diff_result_id': diff_result.id,
                    'changes_detected': diff_result.changes_detected,
                    'change_count': diff_result.change_count,
                    'alignment_score': diff_result.alignment_score,
                    'overlay_ref': diff_result.machine_generated_overlay_ref,
                    'created_at': diff_result.created_at.isoformat() if diff_result.created_at else None
                }
            
            if summary:
                result['summary'] = {
                    'summary_id': summary.id,
                    'summary_text': summary.summary_text,
                    'source': summary.source,
                    'created_at': summary.created_at.isoformat() if summary.created_at else None
                }
            
            return jsonify(result), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting job results: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

