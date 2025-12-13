"""Drawing Management Blueprint
Handles drawing upload and version management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from services.drawing_service import (
    DrawingUploadError,
    DrawingUploadService,
)
from services.orchestrator import OrchestratorService
import logging

# Optional database imports
try:
    from gcp.database import get_db_session
    from gcp.database.models import DrawingVersion
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Database not available: {e}")

logger = logging.getLogger(__name__)

drawings_bp = Blueprint('drawings', __name__, url_prefix='/api/v1/drawings')
upload_service = DrawingUploadService()

# Log blueprint registration
@drawings_bp.before_request
def log_blueprint_request():
    """Log requests to this blueprint"""
    logger.debug(f"Blueprint request: {request.method} {request.path}")
    # Let Flask-CORS handle OPTIONS requests automatically

@drawings_bp.route('/upload', methods=['POST', 'OPTIONS'])
@cross_origin(origins=["http://localhost:3000", "http://localhost:3001"], 
              supports_credentials=True,
              methods=["POST", "OPTIONS"],
              allow_headers=["Content-Type", "Authorization", "X-Requested-With"])
def upload_drawing():
    """Upload a drawing file and optionally create a comparison job"""
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        logger.debug("Handling OPTIONS preflight for /upload")
        response = current_app.make_default_options_response()
        return response
    
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        project_id = request.form.get('project_id', 'default-project')
        # Use ash-system user ID if not provided
        user_id = request.form.get('user_id', 'ash-system-0000000000001')
        file = request.files.get('file')
        old_version_id = request.form.get('old_version_id')

        logger.info(
            "Upload request received",
            extra={
                'project_id': project_id,
                'user_id': user_id,
                'upload_filename': file.filename if file else None,
                'old_version_id': old_version_id,
                'has_file': bool(file)
            }
        )

        if not file:
            return jsonify({'error': 'file required'}), 400

        upload_result = upload_service.handle_upload(
            file_bytes=file.read(),
            filename=file.filename,
            content_type=file.content_type,
            project_id=project_id,
            user_id=user_id,
            is_revision=bool(old_version_id)
        )

        logger.info(
            "Drawing uploaded successfully",
            extra={
                'drawing_version_id': upload_result.drawing_version_id,
                'project_id': upload_result.project_id,
                'drawing_name': upload_result.drawing_name,
                'has_old_version_id': bool(old_version_id)
            }
        )

        job_id = None
        if old_version_id:
            logger.info(
                "Looking up old version for comparison",
                extra={
                    'old_version_id': old_version_id,
                    'new_version_id': upload_result.drawing_version_id,
                    'project_id': upload_result.project_id
                }
            )
            with get_db_session() as db:
                # First try with project_id match
                old_version = db.query(DrawingVersion).filter_by(
                    id=old_version_id,
                    project_id=upload_result.project_id
                ).first()
                
                # If not found, try without project_id constraint (in case project_id differs)
                if not old_version:
                    logger.warning(
                        "Old version not found with project_id match, trying without project_id",
                        extra={'old_version_id': old_version_id, 'project_id': upload_result.project_id}
                    )
                    old_version = db.query(DrawingVersion).filter_by(id=old_version_id).first()
                
                if not old_version:
                    logger.error(
                        "Baseline drawing version not found",
                        extra={
                            'old_version_id': old_version_id,
                            'project_id': upload_result.project_id,
                            'available_versions': [
                                {'id': v.id, 'project_id': v.project_id, 'drawing_name': v.drawing_name}
                                for v in db.query(DrawingVersion).limit(10).all()
                            ]
                        }
                    )
                    return jsonify({'error': 'Baseline drawing version not found'}), 404

                # Get GCS storage paths for streaming job
                old_storage_path = None
                if old_version.drawing and old_version.drawing.storage_path:
                    old_storage_path = old_version.drawing.storage_path
                
                logger.info(
                    "Found old version, creating comparison job",
                    extra={
                        'old_version_id': old_version.id,
                        'old_project_id': old_version.project_id,
                        'new_version_id': upload_result.drawing_version_id,
                        'new_project_id': upload_result.project_id,
                        'old_storage_path': old_storage_path,
                        'new_storage_path': upload_result.storage_path
                    }
                )

            orchestrator = OrchestratorService()
            
            # Use streaming job for multi-page support with real-time progress
            if old_storage_path and upload_result.storage_path:
                try:
                    job_id = orchestrator.create_streaming_job(
                        old_version_id=old_version_id,
                        new_drawing_version_id=upload_result.drawing_version_id,
                        project_id=upload_result.project_id,
                        user_id=user_id,
                        old_pdf_gcs_path=old_storage_path,
                        new_pdf_gcs_path=upload_result.storage_path
                    )
                    logger.info("Streaming job created", extra={'job_id': job_id})
                except Exception as e:
                    logger.warning(f"Streaming job failed, falling back to legacy: {e}")
                    job_id = orchestrator.create_comparison_job(
                        old_version_id=old_version_id,
                        new_drawing_version_id=upload_result.drawing_version_id,
                        project_id=upload_result.project_id,
                        user_id=user_id
                    )
                    logger.info("Legacy comparison job created", extra={'job_id': job_id})
            else:
                # Fallback to legacy job if storage paths not available
                job_id = orchestrator.create_comparison_job(
                    old_version_id=old_version_id,
                    new_drawing_version_id=upload_result.drawing_version_id,
                    project_id=upload_result.project_id,
                    user_id=user_id
                )
                logger.info("Legacy comparison job created (no storage paths)", extra={'job_id': job_id})

        return jsonify({
            'drawing_version_id': upload_result.drawing_version_id,
            'drawing_name': upload_result.drawing_name,
            'version_number': upload_result.version_number,
            'job_id': job_id,
            'status': 'uploaded'
        }), 201
            
    except DrawingUploadError as exc:
        logger.warning(
            "Upload validation failed",
            extra={'project_id': request.form.get('project_id'), 'error': str(exc)}
        )
        return jsonify({'error': str(exc)}), exc.status_code
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@drawings_bp.route('/<drawing_version_id>', methods=['GET'])
def get_drawing(drawing_version_id: str):
    """Get drawing version metadata"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            drawing_version = db.query(DrawingVersion).filter_by(id=drawing_version_id).first()
            if not drawing_version:
                return jsonify({'error': 'Drawing version not found'}), 404
            
            return jsonify({
                'drawing_version_id': drawing_version.id,
                'drawing_name': drawing_version.drawing_name,
                'version_number': drawing_version.version_number,
                'version_label': drawing_version.version_label,
                'project_id': drawing_version.project_id,
                'upload_date': drawing_version.upload_date.isoformat() if drawing_version.upload_date else None,
                'ocr_status': drawing_version.ocr_status,
                'ocr_result_ref': drawing_version.ocr_result_ref,
                'file_size': drawing_version.file_size
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting drawing: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@drawings_bp.route('/<drawing_version_id>/url', methods=['GET'])
def get_drawing_url(drawing_version_id: str):
    """Get a signed URL for viewing/downloading a drawing"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            drawing_version = db.query(DrawingVersion).filter_by(id=drawing_version_id).first()
            if not drawing_version:
                return jsonify({'error': 'Drawing version not found'}), 404
            
            # Get the rasterized image ref (PNG) or fall back to the original file
            image_ref = drawing_version.rasterized_image_ref
            
            # If no rasterized image, try to get from the parent drawing's storage path
            if not image_ref and drawing_version.drawing:
                # Original PDF storage path
                image_ref = drawing_version.drawing.storage_path
            
            if not image_ref:
                return jsonify({'error': 'No image available for this drawing'}), 404
            
            # Generate signed URL
            from gcp.storage import StorageService
            storage = StorageService()
            signed_url = storage.generate_signed_url(image_ref, expiration_minutes=60)
            
            return jsonify({
                'url': signed_url,
                'drawing_name': drawing_version.drawing_name,
                'version_number': drawing_version.version_number
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error getting drawing URL: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@drawings_bp.route('/<drawing_version_id>/versions', methods=['GET'])
def list_versions(drawing_version_id: str):
    """List all versions of a drawing"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    try:
        with get_db_session() as db:
            current_version = db.query(DrawingVersion).filter_by(id=drawing_version_id).first()
            if not current_version:
                return jsonify({'error': 'Drawing version not found'}), 404
            
            # Get all versions of the same drawing
            versions = db.query(DrawingVersion).filter_by(
                project_id=current_version.project_id,
                drawing_name=current_version.drawing_name
            ).order_by(DrawingVersion.version_number).all()
            
            versions_data = []
            for version in versions:
                versions_data.append({
                    'drawing_version_id': version.id,
                    'version_number': version.version_number,
                    'version_label': version.version_label,
                    'upload_date': version.upload_date.isoformat() if version.upload_date else None,
                    'ocr_status': version.ocr_status
                })
            
            return jsonify({
                'drawing_name': current_version.drawing_name,
                'versions': versions_data
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error listing versions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
