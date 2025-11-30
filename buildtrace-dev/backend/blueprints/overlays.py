"""Manual overlay management blueprint."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

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
    """Get a signed URL for the overlay PNG image."""
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
        
        try:
            # Generate signed URL for the image (60 minute expiry)
            signed_url = storage_service.generate_signed_url(overlay_image_ref, expiration_minutes=60)
            return jsonify({
                'diff_result_id': diff_result_id,
                'overlay_image_url': signed_url,
                'page_number': metadata.get('page_number'),
                'drawing_name': metadata.get('drawing_name'),
            })
        except Exception as e:
            return jsonify({'error': f'Failed to generate signed URL: {str(e)}'}), 500


@overlays_bp.route('/<diff_result_id>/images', methods=['GET'])
def get_all_image_urls(diff_result_id: str):
    """Get signed URLs for overlay, baseline, and revised images."""
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
        
        result = {
            'diff_result_id': diff_result_id,
            'page_number': metadata.get('page_number'),
            'drawing_name': metadata.get('drawing_name'),
        }
        
        # Get overlay image URL
        if overlay_image_ref:
            try:
                result['overlay_image_url'] = storage_service.generate_signed_url(
                    overlay_image_ref, expiration_minutes=60
                )
            except Exception as e:
                result['overlay_error'] = str(e)

        # Baseline PNG
        if baseline_image_ref:
            try:
                result['baseline_image_url'] = storage_service.generate_signed_url(
                    baseline_image_ref, expiration_minutes=60
                )
            except Exception as e:
                result['baseline_error'] = str(e)

        # Revised PNG
        if revised_image_ref:
            try:
                result['revised_image_url'] = storage_service.generate_signed_url(
                    revised_image_ref, expiration_minutes=60
                )
            except Exception as e:
                result['revised_error'] = str(e)
        
        # Get baseline and revised drawing versions
        old_version = db.query(DrawingVersion).filter_by(id=diff.old_drawing_version_id).first()
        new_version = db.query(DrawingVersion).filter_by(id=diff.new_drawing_version_id).first()
        
        # For baseline/revised, we'd need to extract the specific page from the PDF
        # For now, return the full PDF URLs - frontend can handle page extraction
        if old_version and old_version.drawing and old_version.drawing.storage_path:
            try:
                result['baseline_pdf_url'] = storage_service.generate_signed_url(
                    old_version.drawing.storage_path, expiration_minutes=60
                )
            except Exception:
                pass
        
        if new_version and new_version.drawing and new_version.drawing.storage_path:
            try:
                result['revised_pdf_url'] = storage_service.generate_signed_url(
                    new_version.drawing.storage_path, expiration_minutes=60
                )
            except Exception:
                pass
        
        return jsonify(result), 200
