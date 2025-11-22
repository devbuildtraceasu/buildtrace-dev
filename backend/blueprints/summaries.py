"""Summary management blueprint."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

try:
    from gcp.database import get_db_session
    from gcp.database.models import ChangeSummary, DiffResult
    DB_AVAILABLE = True
except Exception:  # pragma: no cover
    DB_AVAILABLE = False

summaries_bp = Blueprint('summaries', __name__, url_prefix='/api/v1/summaries')


def _serialize_summary(summary: ChangeSummary) -> dict:
    return {
        'summary_id': summary.id,
        'diff_result_id': summary.diff_result_id,
        'summary_text': summary.summary_text,
        'source': summary.source,
        'ai_model_used': summary.ai_model_used,
        'created_by': summary.created_by,
        'is_active': summary.is_active,
        'created_at': summary.created_at.isoformat() if summary.created_at else None,
        'updated_at': summary.updated_at.isoformat() if summary.updated_at else None,
        'metadata': summary.metadata or {},
    }


@summaries_bp.route('/<diff_result_id>', methods=['GET'])
def get_summary(diff_result_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    with get_db_session() as db:
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
        summaries = (
            db.query(ChangeSummary)
            .filter_by(diff_result_id=diff_result_id)
            .order_by(ChangeSummary.created_at.desc())
            .all()
        )
        active_summary = next((s for s in summaries if s.is_active), None)
        return jsonify({
            'diff_result_id': diff_result_id,
            'active_summary': _serialize_summary(active_summary) if active_summary else None,
            'summaries': [_serialize_summary(s) for s in summaries],
        })


@summaries_bp.route('/<diff_result_id>/regenerate', methods=['POST'])
def regenerate_summary(diff_result_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    data = request.get_json() or {}
    overlay_id = data.get('overlay_id')
    with get_db_session() as db:
        diff = db.query(DiffResult).filter_by(id=diff_result_id).first()
        if not diff:
            return jsonify({'error': 'Diff result not found'}), 404
    from services.orchestrator import OrchestratorService
    orchestrator = OrchestratorService()
    orchestrator.trigger_summary_regeneration(diff_result_id, overlay_id=overlay_id)
    return jsonify({'status': 'queued'})


@summaries_bp.route('/<summary_id>', methods=['PUT'])
def update_summary(summary_id: str):
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    data = request.get_json() or {}
    text = data.get('summary_text')
    with get_db_session() as db:
        summary = db.query(ChangeSummary).filter_by(id=summary_id).first()
        if not summary:
            return jsonify({'error': 'Summary not found'}), 404
        if text:
            summary.summary_text = text
            summary.source = data.get('source', 'human_corrected')
        if 'metadata' in data:
            summary.metadata = data['metadata']
        summary.updated_at = datetime.utcnow()
        summary.is_active = data.get('is_active', True)
        db.flush()
        return jsonify({'summary': _serialize_summary(summary)})
