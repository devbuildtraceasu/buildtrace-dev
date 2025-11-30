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
        
        # Get user_id from authentication middleware
        from utils.auth_helpers import get_current_user_id
        user_id = get_current_user_id()
        if not user_id:
            # Fallback to request data if auth not available (for backward compatibility)
            user_id = data.get('user_id')
        
        if not all([old_version_id, new_drawing_version_id, project_id, user_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        orchestrator = OrchestratorService()
        job_id = orchestrator.create_comparison_job(
            old_version_id=old_version_id,
            new_drawing_version_id=new_drawing_version_id,
            project_id=project_id,
            user_id=user_id
        )
        
        # Query the job to get full details
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job created but not found'}), 500
        
        return jsonify({
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat() if job.created_at else None
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating job: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('', methods=['GET'])
def list_jobs():
    """List recent jobs for a user."""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        limit = request.args.get('limit', default=10, type=int)
        limit = max(1, min(limit, 50))

        with get_db_session() as db:
            query = db.query(Job).order_by(Job.created_at.desc())
            if user_id:
                query = query.filter(Job.created_by == user_id)
            if status:
                query = query.filter(Job.status == status)
            jobs = query.limit(limit).all()

            payload = []
            for job in jobs:
                payload.append({
                    'job_id': job.id,
                    'project_id': job.project_id,
                    'status': job.status,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                })

        return jsonify({'jobs': payload}), 200
    except Exception as e:
        current_app.logger.error(f"Error listing jobs: {e}", exc_info=True)
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

@jobs_bp.route('/<job_id>/ocr-log', methods=['GET'])
def get_ocr_log(job_id: str):
    """Get OCR log file for a job (for display during processing)"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            from gcp.database.models import DrawingVersion
            from gcp.storage import StorageService
            
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Get OCR stages to find drawing versions
            ocr_stages = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='ocr'
            ).all()
            
            if not ocr_stages:
                return jsonify({'error': 'No OCR stages found for this job'}), 404
            
            # Try to get OCR log from the first drawing version
            # Check both old and new versions
            drawing_versions = []
            if job.old_drawing_version_id:
                old_version = db.query(DrawingVersion).filter_by(id=job.old_drawing_version_id).first()
                if old_version and old_version.ocr_result_ref:
                    drawing_versions.append(old_version)
            
            if job.new_drawing_version_id:
                new_version = db.query(DrawingVersion).filter_by(id=job.new_drawing_version_id).first()
                if new_version and new_version.ocr_result_ref:
                    drawing_versions.append(new_version)
            
            # Get OCR results and extract log file refs
            storage = StorageService()
            ocr_logs = []
            
            for version in drawing_versions:
                try:
                    # Download OCR result
                    ocr_data_bytes = storage.download_file(version.ocr_result_ref)
                    import json
                    ocr_data = json.loads(ocr_data_bytes.decode('utf-8'))
                    
                    # Get log file if available
                    log_file_ref = ocr_data.get('log_file_ref')
                    if log_file_ref:
                        try:
                            log_bytes = storage.download_file(log_file_ref)
                            log_data = json.loads(log_bytes.decode('utf-8'))
                            ocr_logs.append({
                                'drawing_version_id': version.id,
                                'drawing_name': version.drawing_name,
                                'log': log_data
                            })
                        except Exception as e:
                            current_app.logger.warning(f"Could not load log file {log_file_ref}: {e}")
                            # Fallback: use summary from OCR data
                            if ocr_data.get('summary'):
                                ocr_logs.append({
                                    'drawing_version_id': version.id,
                                    'drawing_name': version.drawing_name,
                                    'log': {
                                        'summary': ocr_data.get('summary'),
                                        'pages': ocr_data.get('pages', [])
                                    }
                                })
                    elif ocr_data.get('summary'):
                        # Use summary directly if log file not available
                        ocr_logs.append({
                            'drawing_version_id': version.id,
                            'drawing_name': version.drawing_name,
                            'log': {
                                'summary': ocr_data.get('summary'),
                                'pages': ocr_data.get('pages', [])
                            }
                        })
                except Exception as e:
                    current_app.logger.warning(f"Could not load OCR data for version {version.id}: {e}")
                    continue
            
            if not ocr_logs:
                return jsonify({'error': 'No OCR logs found'}), 404
            
            return jsonify({
                'job_id': job_id,
                'ocr_logs': ocr_logs
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting OCR log: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/<job_id>/results', methods=['GET'])
def get_job_results(job_id: str):
    """Get complete job results including diff and summary"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            from gcp.database.models import DiffResult, ChangeSummary, DrawingVersion
            
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            # Get file names from drawing versions
            baseline_file_name = 'Baseline Drawing'
            revised_file_name = 'Revised Drawing'
            
            old_version = db.query(DrawingVersion).filter_by(id=job.old_drawing_version_id).first()
            if old_version and old_version.drawing:
                baseline_file_name = old_version.drawing.original_filename or old_version.drawing.filename or baseline_file_name
            
            new_version = db.query(DrawingVersion).filter_by(id=job.new_drawing_version_id).first()
            if new_version and new_version.drawing:
                revised_file_name = new_version.drawing.original_filename or new_version.drawing.filename or revised_file_name
            
            result = {
                'job_id': job_id,
                'status': job.status,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'baseline_file_name': baseline_file_name,
                'revised_file_name': revised_file_name,
            }
            if job.status != 'completed':
                result['message'] = 'Job still processing'
            
            diff_results = db.query(DiffResult).filter_by(job_id=job_id).order_by(DiffResult.created_at.asc()).all()
            diff_entries = []
            
            # Helper function to parse change types from summary text
            def parse_change_types(summary_text: str) -> dict:
                """Parse added, modified, removed counts from summary text"""
                if not summary_text:
                    return {'added': 0, 'modified': 0, 'removed': 0}
                
                lower_text = summary_text.lower()
                added = len([line for line in summary_text.split('\n') if 'added' in line.lower() or 'addition' in line.lower()])
                removed = len([line for line in summary_text.split('\n') if 'removed' in line.lower() or 'removal' in line.lower()])
                modified = len([line for line in summary_text.split('\n') if 'modified' in line.lower() or 'modification' in line.lower()])
                
                # If no explicit counts, estimate from change_count
                if added == 0 and removed == 0 and modified == 0:
                    # Default: assume all changes are modifications
                    return {'added': 0, 'modified': 1, 'removed': 0}
                
                return {
                    'added': added,
                    'modified': modified,
                    'removed': removed
                }
            
            # Helper function to parse categories from summary text
            def parse_categories(summary_text: str) -> dict:
                """Parse category counts from summary text"""
                categories = {
                    'MEP': 0,
                    'Drywall': 0,
                    'Electrical': 0,
                    'Architectural': 0,
                    'Structural': 0,
                    'Concrete': 0,
                    'Site Work': 0
                }
                
                if not summary_text:
                    return categories
                
                lower_text = summary_text.lower()
                category_keywords = {
                    'MEP': ['mep', 'mechanical', 'plumbing', 'hvac', 'duct', 'pipe', 'ventilation'],
                    'Drywall': ['drywall', 'gypsum', 'sheetrock', 'partition', 'wall board'],
                    'Electrical': ['electrical', 'wiring', 'conduit', 'outlet', 'switch', 'panel', 'circuit'],
                    'Architectural': ['architectural', 'floor plan', 'elevation', 'section', 'detail', 'room'],
                    'Structural': ['structural', 'beam', 'column', 'foundation', 'steel', 'concrete structure'],
                    'Concrete': ['concrete', 'slab', 'pour', 'cement', 'rebar'],
                    'Site Work': ['site', 'excavation', 'grading', 'landscaping', 'paving', 'utilities'],
                }
                
                for category, keywords in category_keywords.items():
                    matches = sum(1 for keyword in keywords if keyword in lower_text)
                    categories[category] = matches
                
                return categories
            
            for diff_result in diff_results:
                metadata = diff_result.diff_metadata or {}
                active_summary = db.query(ChangeSummary).filter_by(
                    diff_result_id=diff_result.id,
                    is_active=True
                ).first()
                summary_payload = None
                change_types = {'added': 0, 'modified': 0, 'removed': 0}
                categories = parse_categories('')
                
                if active_summary:
                    summary_payload = {
                        'summary_id': active_summary.id,
                        'summary_text': active_summary.summary_text,
                        'source': active_summary.source,
                        'created_at': active_summary.created_at.isoformat() if active_summary.created_at else None
                    }
                    # Parse change types and categories from summary
                    change_types = parse_change_types(active_summary.summary_text)
                    categories = parse_categories(active_summary.summary_text)
                
                diff_entries.append({
                    'diff_result_id': diff_result.id,
                    'changes_detected': diff_result.changes_detected,
                    'change_count': diff_result.change_count,
                    'alignment_score': diff_result.alignment_score,
                    'overlay_ref': metadata.get('overlay_image_ref'),
                    'created_at': diff_result.created_at.isoformat() if diff_result.created_at else None,
                    'page_number': metadata.get('page_number'),
                    'drawing_name': metadata.get('drawing_name'),
                    'total_pages': metadata.get('total_pages'),
                    'summary': summary_payload,
                    'change_types': change_types,  # Added, Modified, Removed counts
                    'categories': categories  # Category breakdown
                })

            if diff_entries:
                result['diffs'] = diff_entries
                # Backwards compatibility for clients expecting single diff/summary
                result['diff'] = diff_entries[0]
                if diff_entries[0].get('summary'):
                    result['summary'] = diff_entries[0]['summary']
                
                # Aggregate KPIs across all diffs
                total_added = sum(d.get('change_types', {}).get('added', 0) for d in diff_entries)
                total_modified = sum(d.get('change_types', {}).get('modified', 0) for d in diff_entries)
                total_removed = sum(d.get('change_types', {}).get('removed', 0) for d in diff_entries)
                
                # Aggregate categories across all diffs
                aggregated_categories = {
                    'MEP': 0,
                    'Drywall': 0,
                    'Electrical': 0,
                    'Architectural': 0,
                    'Structural': 0,
                    'Concrete': 0,
                    'Site Work': 0
                }
                for diff_entry in diff_entries:
                    for category, count in diff_entry.get('categories', {}).items():
                        aggregated_categories[category] = aggregated_categories.get(category, 0) + count
                
                result['kpis'] = {
                    'added': total_added,
                    'modified': total_modified,
                    'removed': total_removed
                }
                result['categories'] = aggregated_categories
            
            return jsonify(result), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting job results: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

