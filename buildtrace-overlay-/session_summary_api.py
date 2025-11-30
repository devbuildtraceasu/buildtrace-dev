#!/usr/bin/env python3
"""
Session Summary API Endpoints
Provides aggregated analysis across all pages in a session
"""

from flask import Blueprint, jsonify
from gcp.database import get_db_session
from gcp.database.models import Session, Comparison, AnalysisResult
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

session_summary_bp = Blueprint('session_summary', __name__)

@session_summary_bp.route('/api/session/<session_id>/summary')
def get_session_summary(session_id):
    """
    Get aggregated summary of all analysis results in a session
    """
    try:
        with get_db_session() as db:
            # Get session info
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404

            # Get all comparisons and analysis results
            comparisons = db.query(Comparison).filter_by(session_id=session_id).all()
            analyses = db.query(AnalysisResult).filter_by(session_id=session_id).all()

            # Calculate summary statistics
            total_pages = len(comparisons)
            total_analyses = len(analyses)
            successful_analyses = len([a for a in analyses if a.success])
            failed_analyses = total_analyses - successful_analyses

            # Aggregate critical changes
            critical_changes = []
            all_changes = []
            all_recommendations = []

            for analysis in analyses:
                if analysis.critical_change:
                    critical_changes.append({
                        'drawing_name': analysis.drawing_name,
                        'critical_change': analysis.critical_change
                    })

                if analysis.changes_found:
                    all_changes.extend(analysis.changes_found)

                if analysis.recommendations:
                    all_recommendations.extend(analysis.recommendations)

            # Generate overall summary
            overall_summary = generate_overall_summary(analyses)

            return jsonify({
                'session_id': session_id,
                'session_status': session.status,
                'total_pages': total_pages,
                'total_analyses': total_analyses,
                'successful_analyses': successful_analyses,
                'failed_analyses': failed_analyses,
                'critical_changes_count': len(critical_changes),
                'total_changes_count': len(all_changes),
                'critical_changes': critical_changes,
                'all_changes': all_changes[:10],  # First 10 for preview
                'recommendations': list(set(all_recommendations)),  # Unique recommendations
                'overall_summary': overall_summary,
                'pages': [
                    {
                        'drawing_name': comp.drawing_name,
                        'has_analysis': any(a.comparison_id == comp.id for a in analyses),
                        'changes_detected': comp.changes_detected,
                        'alignment_score': comp.alignment_score
                    }
                    for comp in comparisons
                ]
            })

    except Exception as e:
        logger.error(f"Error getting session summary: {str(e)}")
        return jsonify({'error': 'Failed to get session summary'}), 500


@session_summary_bp.route('/api/session/<session_id>/changes/all')
def get_all_session_changes(session_id):
    """
    Get all changes across all pages in a session
    """
    try:
        with get_db_session() as db:
            analyses = db.query(AnalysisResult).filter_by(session_id=session_id).all()

            all_changes = []
            for analysis in analyses:
                if analysis.changes_found:
                    for change in analysis.changes_found:
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
            })

    except Exception as e:
        logger.error(f"Error getting all session changes: {str(e)}")
        return jsonify({'error': 'Failed to get session changes'}), 500


def generate_overall_summary(analyses):
    """
    Generate an overall summary combining all page analyses
    """
    if not analyses:
        return "No analysis results available."

    successful_analyses = [a for a in analyses if a.success]
    if not successful_analyses:
        return "No successful analyses to summarize."

    # Count pages with critical changes
    critical_pages = len([a for a in successful_analyses if a.critical_change])
    total_pages = len(successful_analyses)

    # Aggregate common themes
    all_summaries = [a.analysis_summary for a in successful_analyses if a.analysis_summary]

    summary_parts = []

    if critical_pages > 0:
        summary_parts.append(f"{critical_pages} of {total_pages} pages have critical changes requiring attention.")
    else:
        summary_parts.append(f"Analyzed {total_pages} pages - no critical issues identified.")

    # Add high-level insights
    if len(all_summaries) > 0:
        summary_parts.append("Common themes include structural modifications, dimensional changes, and detail updates.")

    return " ".join(summary_parts)