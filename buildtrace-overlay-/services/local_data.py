"""
Local file-based data persistence implementation
Stores data as JSON files in local filesystem
"""

import os
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from services.interfaces import (
    DataInterface, SessionData, DrawingData,
    ComparisonData, AnalysisData
)

logger = logging.getLogger(__name__)


class LocalDataService(DataInterface):
    """File-based data persistence using JSON files"""

    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)

        # Create directory structure
        self.sessions_dir = self.data_dir / 'sessions'
        self.drawings_dir = self.data_dir / 'drawings'
        self.comparisons_dir = self.data_dir / 'comparisons'
        self.analyses_dir = self.data_dir / 'analyses'
        self.chat_dir = self.data_dir / 'chat'

        for directory in [self.sessions_dir, self.drawings_dir,
                         self.comparisons_dir, self.analyses_dir, self.chat_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Local data service initialized with directory: {self.data_dir}")

    # Session operations
    def save_session(self, session: SessionData) -> bool:
        """Save session data to JSON file"""
        try:
            session_file = self.sessions_dir / f"{session.id}.json"
            session_dict = self._session_to_dict(session)

            with open(session_file, 'w') as f:
                json.dump(session_dict, f, indent=2, default=str)

            logger.info(f"Session saved: {session.id}")
            return True

        except Exception as e:
            logger.error(f"Error saving session {session.id}: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            if not session_file.exists():
                return None

            with open(session_file, 'r') as f:
                session_dict = json.load(f)

            return self._dict_to_session(session_dict)

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    def list_sessions(self, user_id: Optional[str] = None,
                     limit: int = 50, offset: int = 0) -> List[SessionData]:
        """List sessions with optional user filtering"""
        try:
            sessions = []
            session_files = list(self.sessions_dir.glob("*.json"))

            # Sort by modification time (newest first)
            session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            for session_file in session_files[offset:offset + limit]:
                try:
                    with open(session_file, 'r') as f:
                        session_dict = json.load(f)

                    session = self._dict_to_session(session_dict)

                    # Filter by user if specified
                    if user_id is None or session.user_id == user_id:
                        sessions.append(session)

                except Exception as e:
                    logger.warning(f"Error loading session file {session_file}: {e}")

            return sessions[:limit]

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False

            session.status = status
            session.updated_at = datetime.utcnow()
            return self.save_session(session)

        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete session and related data"""
        try:
            # Delete session file
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()

            # Delete related drawings
            for drawing_file in self.drawings_dir.glob(f"{session_id}_*.json"):
                drawing_file.unlink()

            # Delete related comparisons
            for comparison_file in self.comparisons_dir.glob(f"{session_id}_*.json"):
                comparison_file.unlink()

            # Delete related analyses
            for analysis_file in self.analyses_dir.glob(f"*_{session_id}_*.json"):
                analysis_file.unlink()

            # Delete chat history
            chat_file = self.chat_dir / f"{session_id}.json"
            if chat_file.exists():
                chat_file.unlink()

            logger.info(f"Session deleted: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    # Drawing operations
    def save_drawing(self, drawing: DrawingData) -> bool:
        """Save drawing data"""
        try:
            drawing_file = self.drawings_dir / f"{drawing.session_id}_{drawing.id}.json"
            drawing_dict = self._drawing_to_dict(drawing)

            with open(drawing_file, 'w') as f:
                json.dump(drawing_dict, f, indent=2, default=str)

            logger.info(f"Drawing saved: {drawing.id}")
            return True

        except Exception as e:
            logger.error(f"Error saving drawing {drawing.id}: {e}")
            return False

    def get_drawings(self, session_id: str) -> List[DrawingData]:
        """Get all drawings for a session"""
        try:
            drawings = []
            pattern = f"{session_id}_*.json"

            for drawing_file in self.drawings_dir.glob(pattern):
                try:
                    with open(drawing_file, 'r') as f:
                        drawing_dict = json.load(f)

                    drawings.append(self._dict_to_drawing(drawing_dict))

                except Exception as e:
                    logger.warning(f"Error loading drawing file {drawing_file}: {e}")

            return drawings

        except Exception as e:
            logger.error(f"Error getting drawings for session {session_id}: {e}")
            return []

    def get_drawing(self, drawing_id: str) -> Optional[DrawingData]:
        """Get drawing by ID"""
        try:
            # Since we don't know the session_id, we need to search
            for drawing_file in self.drawings_dir.glob("*.json"):
                try:
                    with open(drawing_file, 'r') as f:
                        drawing_dict = json.load(f)

                    if drawing_dict.get('id') == drawing_id:
                        return self._dict_to_drawing(drawing_dict)

                except Exception as e:
                    logger.warning(f"Error checking drawing file {drawing_file}: {e}")

            return None

        except Exception as e:
            logger.error(f"Error getting drawing {drawing_id}: {e}")
            return None

    # Comparison operations
    def save_comparison(self, comparison: ComparisonData) -> bool:
        """Save comparison result"""
        try:
            comparison_file = self.comparisons_dir / f"{comparison.session_id}_{comparison.id}.json"
            comparison_dict = self._comparison_to_dict(comparison)

            with open(comparison_file, 'w') as f:
                json.dump(comparison_dict, f, indent=2, default=str)

            logger.info(f"Comparison saved: {comparison.id}")
            return True

        except Exception as e:
            logger.error(f"Error saving comparison {comparison.id}: {e}")
            return False

    def get_comparisons(self, session_id: str) -> List[ComparisonData]:
        """Get all comparisons for a session"""
        try:
            comparisons = []
            pattern = f"{session_id}_*.json"

            for comparison_file in self.comparisons_dir.glob(pattern):
                try:
                    with open(comparison_file, 'r') as f:
                        comparison_dict = json.load(f)

                    comparisons.append(self._dict_to_comparison(comparison_dict))

                except Exception as e:
                    logger.warning(f"Error loading comparison file {comparison_file}: {e}")

            return comparisons

        except Exception as e:
            logger.error(f"Error getting comparisons for session {session_id}: {e}")
            return []

    def get_comparison(self, comparison_id: str) -> Optional[ComparisonData]:
        """Get comparison by ID"""
        try:
            for comparison_file in self.comparisons_dir.glob("*.json"):
                try:
                    with open(comparison_file, 'r') as f:
                        comparison_dict = json.load(f)

                    if comparison_dict.get('id') == comparison_id:
                        return self._dict_to_comparison(comparison_dict)

                except Exception as e:
                    logger.warning(f"Error checking comparison file {comparison_file}: {e}")

            return None

        except Exception as e:
            logger.error(f"Error getting comparison {comparison_id}: {e}")
            return None

    # Analysis operations
    def save_analysis(self, analysis: AnalysisData) -> bool:
        """Save analysis result"""
        try:
            analysis_file = self.analyses_dir / f"{analysis.comparison_id}_{analysis.id}.json"
            analysis_dict = self._analysis_to_dict(analysis)

            with open(analysis_file, 'w') as f:
                json.dump(analysis_dict, f, indent=2, default=str)

            logger.info(f"Analysis saved: {analysis.id}")
            return True

        except Exception as e:
            logger.error(f"Error saving analysis {analysis.id}: {e}")
            return False

    def get_analyses(self, session_id: str) -> List[AnalysisData]:
        """Get all analyses for a session"""
        try:
            analyses = []

            # Get comparisons for this session first
            comparisons = self.get_comparisons(session_id)
            comparison_ids = [c.id for c in comparisons]

            for analysis_file in self.analyses_dir.glob("*.json"):
                try:
                    with open(analysis_file, 'r') as f:
                        analysis_dict = json.load(f)

                    if analysis_dict.get('comparison_id') in comparison_ids:
                        analyses.append(self._dict_to_analysis(analysis_dict))

                except Exception as e:
                    logger.warning(f"Error loading analysis file {analysis_file}: {e}")

            return analyses

        except Exception as e:
            logger.error(f"Error getting analyses for session {session_id}: {e}")
            return []

    def get_analysis_by_comparison(self, comparison_id: str) -> Optional[AnalysisData]:
        """Get analysis by comparison ID"""
        try:
            pattern = f"{comparison_id}_*.json"

            for analysis_file in self.analyses_dir.glob(pattern):
                try:
                    with open(analysis_file, 'r') as f:
                        analysis_dict = json.load(f)

                    return self._dict_to_analysis(analysis_dict)

                except Exception as e:
                    logger.warning(f"Error loading analysis file {analysis_file}: {e}")

            return None

        except Exception as e:
            logger.error(f"Error getting analysis for comparison {comparison_id}: {e}")
            return None

    # Chat operations
    def save_chat_message(self, session_id: str, role: str, content: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save chat message"""
        try:
            chat_file = self.chat_dir / f"{session_id}.json"

            # Load existing messages
            messages = []
            if chat_file.exists():
                with open(chat_file, 'r') as f:
                    messages = json.load(f)

            # Add new message
            message = {
                'id': str(uuid.uuid4()),
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
            messages.append(message)

            # Save updated messages
            with open(chat_file, 'w') as f:
                json.dump(messages, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Error saving chat message for session {session_id}: {e}")
            return False

    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for session"""
        try:
            chat_file = self.chat_dir / f"{session_id}.json"

            if not chat_file.exists():
                return []

            with open(chat_file, 'r') as f:
                messages = json.load(f)

            # Return most recent messages first
            return messages[-limit:]

        except Exception as e:
            logger.error(f"Error getting chat history for session {session_id}: {e}")
            return []

    # Utility operations
    def cleanup_old_sessions(self, older_than_hours: int = 24) -> int:
        """Clean up old sessions"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            cleaned_count = 0

            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if mtime < cutoff_time:
                        # Get session ID from filename
                        session_id = session_file.stem
                        if self.delete_session(session_id):
                            cleaned_count += 1

                except Exception as e:
                    logger.warning(f"Error cleaning session file {session_file}: {e}")

            logger.info(f"Cleaned up {cleaned_count} old sessions")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about sessions"""
        try:
            stats = {
                'total_sessions': len(list(self.sessions_dir.glob("*.json"))),
                'total_drawings': len(list(self.drawings_dir.glob("*.json"))),
                'total_comparisons': len(list(self.comparisons_dir.glob("*.json"))),
                'total_analyses': len(list(self.analyses_dir.glob("*.json"))),
                'storage_type': 'local_file'
            }

            # Get recent activity
            recent_sessions = self.list_sessions(limit=10)
            if recent_sessions:
                stats['most_recent_session'] = recent_sessions[0].created_at.isoformat() if recent_sessions[0].created_at else None

            return stats

        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {'error': str(e)}

    # Helper methods for data conversion
    def _session_to_dict(self, session: SessionData) -> Dict[str, Any]:
        """Convert SessionData to dictionary"""
        return {
            'id': session.id,
            'user_id': session.user_id,
            'project_id': session.project_id,
            'session_type': session.session_type,
            'status': session.status,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'updated_at': session.updated_at.isoformat() if session.updated_at else None,
            'total_time': session.total_time,
            'metadata': session.metadata
        }

    def _dict_to_session(self, data: Dict[str, Any]) -> SessionData:
        """Convert dictionary to SessionData"""
        return SessionData(
            id=data['id'],
            user_id=data.get('user_id'),
            project_id=data.get('project_id'),
            session_type=data.get('session_type', 'comparison'),
            status=data.get('status', 'active'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            total_time=data.get('total_time'),
            metadata=data.get('metadata')
        )

    def _drawing_to_dict(self, drawing: DrawingData) -> Dict[str, Any]:
        """Convert DrawingData to dictionary"""
        return {
            'id': drawing.id,
            'session_id': drawing.session_id,
            'drawing_type': drawing.drawing_type,
            'filename': drawing.filename,
            'original_filename': drawing.original_filename,
            'storage_path': drawing.storage_path,
            'drawing_name': drawing.drawing_name,
            'page_number': drawing.page_number,
            'processed_at': drawing.processed_at.isoformat() if drawing.processed_at else None,
            'metadata': drawing.metadata
        }

    def _dict_to_drawing(self, data: Dict[str, Any]) -> DrawingData:
        """Convert dictionary to DrawingData"""
        return DrawingData(
            id=data['id'],
            session_id=data['session_id'],
            drawing_type=data['drawing_type'],
            filename=data['filename'],
            original_filename=data['original_filename'],
            storage_path=data['storage_path'],
            drawing_name=data.get('drawing_name'),
            page_number=data.get('page_number'),
            processed_at=datetime.fromisoformat(data['processed_at']) if data.get('processed_at') else None,
            metadata=data.get('metadata')
        )

    def _comparison_to_dict(self, comparison: ComparisonData) -> Dict[str, Any]:
        """Convert ComparisonData to dictionary"""
        return {
            'id': comparison.id,
            'session_id': comparison.session_id,
            'old_drawing_id': comparison.old_drawing_id,
            'new_drawing_id': comparison.new_drawing_id,
            'drawing_name': comparison.drawing_name,
            'overlay_path': comparison.overlay_path,
            'old_image_path': comparison.old_image_path,
            'new_image_path': comparison.new_image_path,
            'alignment_score': comparison.alignment_score,
            'changes_detected': comparison.changes_detected,
            'created_at': comparison.created_at.isoformat() if comparison.created_at else None
        }

    def _dict_to_comparison(self, data: Dict[str, Any]) -> ComparisonData:
        """Convert dictionary to ComparisonData"""
        return ComparisonData(
            id=data['id'],
            session_id=data['session_id'],
            old_drawing_id=data['old_drawing_id'],
            new_drawing_id=data['new_drawing_id'],
            drawing_name=data['drawing_name'],
            overlay_path=data.get('overlay_path'),
            old_image_path=data.get('old_image_path'),
            new_image_path=data.get('new_image_path'),
            alignment_score=data.get('alignment_score'),
            changes_detected=data.get('changes_detected', False),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        )

    def _analysis_to_dict(self, analysis: AnalysisData) -> Dict[str, Any]:
        """Convert AnalysisData to dictionary"""
        return {
            'id': analysis.id,
            'comparison_id': analysis.comparison_id,
            'drawing_name': analysis.drawing_name,
            'changes_found': analysis.changes_found,
            'critical_change': analysis.critical_change,
            'analysis_summary': analysis.analysis_summary,
            'recommendations': analysis.recommendations,
            'success': analysis.success,
            'error_message': analysis.error_message,
            'ai_model_used': analysis.ai_model_used,
            'created_at': analysis.created_at.isoformat() if analysis.created_at else None
        }

    def _dict_to_analysis(self, data: Dict[str, Any]) -> AnalysisData:
        """Convert dictionary to AnalysisData"""
        return AnalysisData(
            id=data['id'],
            comparison_id=data['comparison_id'],
            drawing_name=data['drawing_name'],
            changes_found=data.get('changes_found'),
            critical_change=data.get('critical_change'),
            analysis_summary=data.get('analysis_summary'),
            recommendations=data.get('recommendations'),
            success=data.get('success', True),
            error_message=data.get('error_message'),
            ai_model_used=data.get('ai_model_used', 'gpt-4o'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        )