"""Manual overlay management blueprint."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app, Response

from gcp.storage import StorageService

try:
    from gcp.database import get_db_session
    from gcp.database.models import DiffResult, ManualOverlay
    DB_AVAILABLE = True
except Exception:  # pragma: no cover
    DB_AVAILABLE = False

logger_name = __name__

overlays_bp = Blueprint('overlays', __name__, url_prefix='/api/v1/overlays')
storage_service = StorageService()


def _serialize_overlay(overlay: ManualOverlay) -> dict:
    return {
        'overlay_id': overlay.id,
        'diff_result_id': overlay.diff_result_id,
        'overlay_ref': overlay.overlay_ref,
        'created_by': overlay.created_by,
        'is_active': overlay.is_active,
        'created_at': overlay.created_at.isoformat() if overlay.created_at else None,
        'updated_at': overlay.updated_at.isoformat() if overlay.updated_at else None,
        'metadata': overlay.metadata or {},
    }


@overlays_bp.route('/<diff_result_id>', methods=['GET'])
def get_overlays(diff_result_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
        overlays = (
            db.query(ManualOverlay)
            .filter_by(diff_result_id=diff_result_id)
            .order_by(ManualOverlay.created_at.desc())
            .all()
        )
        active_overlay = next((o for o in overlays if o.is_active), None)
        active_payload = None
        if active_overlay and active_overlay.overlay_ref:
            try:
                raw = storage_service.download_file(active_overlay.overlay_ref)
                active_payload = json.loads(raw.decode('utf-8'))
            except Exception as exc:  # pragma: no cover
                active_payload = {'error': str(exc)}
        machine_payload = None
        if diff.machine_generated_overlay_ref:
            try:
                raw = storage_service.download_file(diff.machine_generated_overlay_ref)
                machine_payload = json.loads(raw.decode('utf-8'))
            except Exception:
                machine_payload = None
        return jsonify({
            'diff_result_id': diff_result_id,
            'machine_overlay_ref': diff.machine_generated_overlay_ref,
            'machine_overlay': machine_payload,
            'active_overlay': _serialize_overlay(active_overlay) if active_overlay else None,
            'active_overlay_data': active_payload,
            'overlays': [_serialize_overlay(o) for o in overlays],
        })


@overlays_bp.route('/<diff_result_id>/manual', methods=['POST'])
def create_manual_overlay(diff_result_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    payload = request.get_json() or {}
    overlay_data = payload.get('overlay_data')
    created_by = payload.get('user_id', 'system')
    metadata = payload.get('metadata') or {}
    auto_regenerate = bool(payload.get('auto_regenerate'))
    if overlay_data is None:
        return jsonify({'error': 'overlay_data is required'}), 400
    overlay_id = str(uuid.uuid4())
    overlay_ref = storage_service.upload_overlay(overlay_id, overlay_data)
    with get_db_session() as db:
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
        db.query(ManualOverlay).filter_by(diff_result_id=diff_result_id, is_active=True).update({'is_active': False})
        overlay = ManualOverlay(
            id=overlay_id,
            diff_result_id=diff_result_id,
            overlay_ref=overlay_ref,
            created_by=created_by,
            is_active=True,
            metadata=metadata,
        )
        db.add(overlay)
        db.flush()
        response = {'overlay': _serialize_overlay(overlay)}
        if auto_regenerate:
            from services.orchestrator import OrchestratorService
            orchestrator = OrchestratorService()
            orchestrator.trigger_summary_regeneration(diff_result_id, overlay_id=overlay.id)
            response['summary_regeneration'] = 'triggered'
        return jsonify(response), 201


@overlays_bp.route('/<diff_result_id>/manual/<overlay_id>', methods=['PUT'])
def update_manual_overlay(diff_result_id: str, overlay_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    payload = request.get_json() or {}
    overlay_data = payload.get('overlay_data')
    with get_db_session() as db:
        overlay = db.query(ManualOverlay).filter_by(id=overlay_id, diff_result_id=diff_result_id).first()
        if not overlay:
            return jsonify({'error': 'Overlay not found'}), 404
        if overlay_data is not None:
            overlay.overlay_ref = storage_service.upload_overlay(overlay_id, overlay_data)
        if 'is_active' in payload:
            overlay.is_active = bool(payload['is_active'])
        if 'metadata' in payload:
            overlay.metadata = payload['metadata']
        overlay.updated_at = datetime.utcnow()
        db.flush()
        return jsonify({'overlay': _serialize_overlay(overlay)})


@overlays_bp.route('/<diff_result_id>/manual/<overlay_id>', methods=['DELETE'])
def delete_manual_overlay(diff_result_id: str, overlay_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        overlay = db.query(ManualOverlay).filter_by(id=overlay_id, diff_result_id=diff_result_id).first()
        if not overlay:
            return jsonify({'error': 'Overlay not found'}), 404
        overlay.is_active = False
        overlay.updated_at = datetime.utcnow()
        db.flush()
        return jsonify({'status': 'deleted'})


@overlays_bp.route('/<diff_result_id>/image-url', methods=['GET'])
def get_overlay_image_url(diff_result_id: str):
    """Get proxy URL for the overlay PNG image."""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    with get_db_session() as db:
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
        
        # Get overlay image path from diff_metadata
        metadata = diff.diff_metadata or {}
        overlay_image_ref = metadata.get('overlay_image_ref')
        
        if not overlay_image_ref:
            return jsonify({'error': 'No overlay image available'}), 404
        
        # Return absolute proxy URL with backend host
        host_url = request.host_url.rstrip('/')
        return jsonify({
            'diff_result_id': diff_result_id,
            'overlay_image_url': f"{host_url}/api/v1/overlays/{diff_result_id}/image/overlay",
            'page_number': metadata.get('page_number'),
            'drawing_name': metadata.get('drawing_name'),
        })


@overlays_bp.route('/<diff_result_id>/images', methods=['GET'])
def get_all_image_urls(diff_result_id: str):
    """Get proxy URLs for overlay, baseline, and revised images.
    
    Uses proxy endpoints instead of signed URLs to avoid service account key issues.
    """
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    with get_db_session() as db:
        from gcp.database.models import DrawingVersion
        
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
        
        metadata = diff.diff_metadata or {}
        overlay_image_ref = metadata.get('overlay_image_ref')
        baseline_image_ref = metadata.get('baseline_image_ref')
        revised_image_ref = metadata.get('revised_image_ref')
        
        # Use absolute proxy URLs with backend host
        # Get the request host URL (will be the backend domain)
        host_url = request.host_url.rstrip('/')
        base_proxy_url = f"{host_url}/api/v1/overlays/{diff_result_id}/image"
        
        result = {
            'diff_result_id': diff_result_id,
            'page_number': metadata.get('page_number'),
            'drawing_name': metadata.get('drawing_name'),
        }
        
        # Get overlay image URL via proxy
        if overlay_image_ref:
            result['overlay_image_url'] = f"{base_proxy_url}/overlay"

        # Baseline PNG via proxy
        if baseline_image_ref:
            result['baseline_image_url'] = f"{base_proxy_url}/baseline"

        # Revised PNG via proxy
        if revised_image_ref:
            result['revised_image_url'] = f"{base_proxy_url}/revised"
        
        return jsonify(result), 200


@overlays_bp.route('/<diff_result_id>/image/<image_type>', methods=['GET'])
def get_image_proxy(diff_result_id: str, image_type: str):
    """
    Proxy endpoint to serve images directly from GCS.
    This bypasses signed URLs which require service account keys.
    image_type can be: 'overlay', 'baseline', 'revised'
    """
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    valid_types = ['overlay', 'baseline', 'revised']
    if image_type not in valid_types:
        return jsonify({'error': f'Invalid image type. Must be one of: {valid_types}'}), 400
    
    with get_db_session() as db:
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
        
        metadata = diff.diff_metadata or {}
        
        # Map image type to metadata key
        ref_key_map = {
            'overlay': 'overlay_image_ref',
            'baseline': 'baseline_image_ref',
            'revised': 'revised_image_ref'
        }
        
        image_ref = metadata.get(ref_key_map[image_type])
        
        if not image_ref:
            return jsonify({'error': f'No {image_type} image available'}), 404
        
        try:
            # Download image content directly from GCS
            image_bytes = storage_service.download_file(image_ref)
            
            if not image_bytes:
                current_app.logger.warning(f"Image file is empty: {image_ref}")
                return jsonify({'error': f'Image file is empty'}), 404
            
            # Determine content type
            import mimetypes
            content_type = 'image/png'
            if image_ref.lower().endswith('.jpg') or image_ref.lower().endswith('.jpeg'):
                content_type = 'image/jpeg'
            
            return Response(
                image_bytes,
                mimetype=content_type,
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Content-Disposition': f'inline; filename="{image_type}_{diff_result_id}.png"'
                }
            )
        except FileNotFoundError as e:
            current_app.logger.warning(f"Image file not found: {image_ref} - {e}")
            return jsonify({'error': f'Image file not found'}), 404
        except Exception as e:
            current_app.logger.error(f"Failed to proxy image {image_type} for diff {diff_result_id}: {e}", exc_info=True)
            return jsonify({'error': f'Failed to load image: {str(e)}'}), 500
