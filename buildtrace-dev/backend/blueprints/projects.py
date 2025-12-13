"""Projects blueprint for CRUD operations."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import asc, func
import logging

logger = logging.getLogger(__name__)

try:
    from gcp.database import get_db_session
    from gcp.database.models import Project, Organization, User, DrawingVersion, Job, DiffResult, Drawing
    DB_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    DB_AVAILABLE = False
    raise_exc = exc

projects_bp = Blueprint('projects', __name__, url_prefix='/api/v1/projects')


def _get_project_counts(project_id: str, db) -> dict:
    """Get document, drawing, and comparison counts for a project"""
    # Count drawing versions (drawings)
    drawing_count = db.query(func.count(DrawingVersion.id)).filter_by(
        project_id=project_id
    ).scalar() or 0
    
    # Count unique source files (documents) - group by original filename
    drawing_versions = db.query(DrawingVersion).filter_by(project_id=project_id).all()
    unique_files = set()
    for dv in drawing_versions:
        if dv.drawing:
            unique_files.add(dv.drawing.original_filename)
    document_count = len(unique_files)
    
    # Count jobs (comparisons)
    comparison_count = db.query(func.count(Job.id)).filter_by(
        project_id=project_id
    ).scalar() or 0
    
    return {
        'document_count': document_count,
        'drawing_count': drawing_count,
        'comparison_count': comparison_count
    }


def _serialize_project(project: Project, db=None, include_counts: bool = False) -> dict:
    """Serialize project with optional stats"""
    result = {
        'project_id': project.id,
        'name': project.name,
        'description': project.description,
        'project_number': project.project_number,
        'client_name': project.client_name,
        'location': project.location,
        'status': project.status,
        'user_id': project.user_id,
        'owner_id': project.user_id,  # Alias for frontend compatibility
        'organization_id': project.organization_id,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None,
    }
    
    # Add counts if db session is provided and counts requested
    if db and include_counts:
        counts = _get_project_counts(project.id, db)
        result.update(counts)
    else:
        # Default counts to 0 if not fetching
        result['document_count'] = 0
        result['drawing_count'] = 0
        result['comparison_count'] = 0
    
    return result


@projects_bp.route('', methods=['GET'])
def list_projects():
    """List all projects for a user, optionally with counts"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    user_id = request.args.get('user_id')
    org_id = request.args.get('organization_id')
    include_counts = request.args.get('include_counts', 'true').lower() == 'true'
    
    with get_db_session() as db:
        query = db.query(Project).order_by(asc(Project.created_at))
        if user_id:
            query = query.filter(Project.user_id == user_id)
        if org_id:
            query = query.filter(Project.organization_id == org_id)
        projects = query.all()
        
        serialized = [_serialize_project(p, db, include_counts) for p in projects]
        return jsonify({'success': True, 'projects': serialized})


@projects_bp.route('', methods=['POST'])
def create_project():
    """Create a new project"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Database not available'}), 503
    data = request.get_json() or {}
    name = data.get('name')
    user_id = data.get('user_id')
    if not name or not user_id:
        return jsonify({'success': False, 'error': 'name and user_id are required'}), 400
    with get_db_session() as db:
        owner = db.query(User).filter_by(id=user_id).first()
        if not owner:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        project = Project(
            name=name,
            user_id=user_id,
            description=data.get('description'),
            project_number=data.get('project_number'),
            client_name=data.get('client_name'),
            location=data.get('location'),
            status=data.get('status', 'active'),
            organization_id=data.get('organization_id') or owner.organization_id,
        )
        db.add(project)
        db.flush()
        current_app.logger.info('Project created', extra={'project_id': project.id})
        return jsonify({'success': True, 'project': _serialize_project(project, db, include_counts=True)}), 201


@projects_bp.route('/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """Get a single project by ID with counts"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        return jsonify({'success': True, 'project': _serialize_project(project, db, include_counts=True)})


@projects_bp.route('/<project_id>', methods=['PUT'])
def update_project(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    data = request.get_json() or {}
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        for field in ['name', 'description', 'project_number', 'client_name', 'location', 'status']:
            if field in data:
                setattr(project, field, data[field])
        if 'organization_id' in data:
            project.organization_id = data['organization_id']
        db.flush()
        return jsonify({'project': _serialize_project(project)})


@projects_bp.route('/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        db.delete(project)
        return jsonify({'status': 'deleted'})


@projects_bp.route('/<project_id>/members', methods=['GET'])
def list_project_members(project_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        owner = db.query(User).filter_by(id=project.user_id).first()
        members = []
        if owner:
            members.append({
                'user_id': owner.id,
                'name': owner.name,
                'email': owner.email,
                'role': owner.role or 'owner'
            })
        return jsonify({'project_id': project_id, 'members': members})


# ============================================================================
# NEW ENDPOINTS FOR FRONTEND SUPPORT
# ============================================================================

@projects_bp.route('/<project_id>/documents', methods=['GET'])
def list_project_documents(project_id: str):
    """List documents (unique source files) in a project"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Database not available'}), 503
    
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Get all drawing versions for this project
        drawing_versions = db.query(DrawingVersion).filter_by(
            project_id=project_id
        ).order_by(DrawingVersion.upload_date.desc()).all()
        
        # Group by source file (using drawing relationship to get original filename)
        documents = {}
        for dv in drawing_versions:
            drawing = dv.drawing
            if drawing:
                source_file = drawing.original_filename
                if source_file not in documents:
                    documents[source_file] = {
                        'document_id': drawing.id,
                        'name': source_file,
                        'project_id': project_id,
                        'file_type': 'application/pdf',
                        'file_size': dv.file_size or 0,
                        'uploaded_at': dv.upload_date.isoformat() if dv.upload_date else None,
                        'page_count': 0,
                        'status': 'ready' if dv.ocr_status == 'completed' else (dv.ocr_status or 'pending'),
                        'version': 'revised' if dv.version_number > 1 else 'baseline'
                    }
                documents[source_file]['page_count'] += 1
        
        return jsonify({'success': True, 'documents': list(documents.values())})


@projects_bp.route('/<project_id>/drawings', methods=['GET'])
def list_project_drawings(project_id: str):
    """List all drawings (pages) in a project"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Database not available'}), 503
    
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Get all drawing versions with their drawings
        drawing_versions = db.query(DrawingVersion).filter_by(
            project_id=project_id
        ).order_by(DrawingVersion.drawing_name, DrawingVersion.version_number).all()
        
        drawings = []
        for dv in drawing_versions:
            drawing = dv.drawing
            drawings.append({
                'drawing_id': dv.id,
                'document_id': drawing.id if drawing else None,
                'project_id': project_id,
                'name': dv.drawing_name or f'Page-{dv.version_number}',
                'page_number': dv.version_number,
                'source_document': drawing.original_filename if drawing else 'Unknown',
                'version': 'revised' if dv.version_number > 1 else 'baseline',
                'auto_detected': True,  # OCR auto-detects drawing numbers
                'created_at': dv.upload_date.isoformat() if dv.upload_date else None,
                'ocr_status': dv.ocr_status or 'pending',
                'thumbnail_url': None  # Could be generated from rasterized_image_ref
            })
        
        return jsonify({'success': True, 'drawings': drawings})


@projects_bp.route('/<project_id>/comparisons', methods=['GET'])
def list_project_comparisons(project_id: str):
    """List all comparisons (jobs) in a project"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Database not available'}), 503
    
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Get all jobs for this project
        jobs = db.query(Job).filter_by(
            project_id=project_id
        ).order_by(Job.created_at.desc()).all()
        
        comparisons = []
        for job in jobs:
            # Get diff result for change count
            diff_result = db.query(DiffResult).filter_by(job_id=job.id).first()
            
            # Get drawing names from versions
            old_version = db.query(DrawingVersion).filter_by(id=job.old_drawing_version_id).first()
            new_version = db.query(DrawingVersion).filter_by(id=job.new_drawing_version_id).first()
            
            comparisons.append({
                'comparison_id': job.id,
                'project_id': project_id,
                'baseline_drawing_id': job.old_drawing_version_id,
                'revised_drawing_id': job.new_drawing_version_id,
                'baseline_drawing_name': old_version.drawing_name if old_version else 'Unknown',
                'revised_drawing_name': new_version.drawing_name if new_version else 'Unknown',
                'job_id': job.id,
                'status': job.status,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'change_count': diff_result.change_count if diff_result else 0
            })
        
        return jsonify({'success': True, 'comparisons': comparisons})


@projects_bp.route('/<project_id>/stats', methods=['GET'])
def get_project_stats(project_id: str):
    """Get project statistics (counts for documents, drawings, comparisons)"""
    if not DB_AVAILABLE:
        return jsonify({'success': False, 'error': 'Database not available'}), 503
    
    with get_db_session() as db:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        counts = _get_project_counts(project_id, db)
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            **counts
        })


# Document URL endpoint - separate from project routes
documents_bp = Blueprint('documents', __name__, url_prefix='/api/v1/documents')


@documents_bp.route('/<document_id>/url', methods=['GET'])
def get_document_url(document_id: str):
    """Get a signed URL for viewing/downloading a document from GCS"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        from gcp.storage import StorageService
        storage = StorageService()
        
        with get_db_session() as db:
            # Try finding by drawing ID first (this is what document_id is set to in list endpoint)
            drawing = db.query(Drawing).filter_by(id=document_id).first()
            
            if drawing:
                # Get the latest version for this drawing
                latest_version = db.query(DrawingVersion).filter_by(
                    drawing_id=drawing.id
                ).order_by(DrawingVersion.version_number.desc()).first()
                
                if latest_version:
                    # Try storage_path from drawing first (original PDF)
                    storage_path = None
                    if drawing.storage_path:
                        storage_path = drawing.storage_path
                    elif latest_version.storage_path:
                        storage_path = latest_version.storage_path
                    
                    if storage_path:
                        try:
                            signed_url = storage.generate_signed_url(storage_path, expiration_minutes=60)
                            if signed_url:
                                # Return format expected by frontend: { url: string }
                                return jsonify({'url': signed_url})
                        except Exception as url_error:
                            logger.warning(f"Could not generate signed URL for {storage_path}: {url_error}")
            
            # Also try finding by drawing version ID (fallback)
            drawing_version = db.query(DrawingVersion).filter_by(id=document_id).first()
            if drawing_version:
                storage_path = None
                if drawing_version.drawing and drawing_version.drawing.storage_path:
                    storage_path = drawing_version.drawing.storage_path
                elif drawing_version.storage_path:
                    storage_path = drawing_version.storage_path
                
                if storage_path:
                    try:
                        signed_url = storage.generate_signed_url(storage_path, expiration_minutes=60)
                        if signed_url:
                            return jsonify({'url': signed_url})
                    except Exception as url_error:
                        logger.warning(f"Could not generate signed URL for {storage_path}: {url_error}")
            
            return jsonify({'error': 'Document not found or no storage path'}), 404
            
    except Exception as e:
        logger.error(f"Error generating document URL: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
