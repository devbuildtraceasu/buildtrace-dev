#!/usr/bin/env python3
"""
Session Service

Manages session-based processing for backward compatibility with buildtrace-overlay-
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session as DBSession
from gcp.database.models import Session, Drawing, Comparison, AnalysisResult, ChatConversation
from config import config

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing sessions"""
    
    def __init__(self, db_session: DBSession):
        """
        Initialize session service
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def create_session(self, user_id: Optional[str] = None, project_id: Optional[str] = None,
                      session_type: str = 'comparison', metadata: Optional[Dict] = None) -> Session:
        """
        Create a new session
        
        Args:
            user_id: User ID (optional for anonymous sessions)
            project_id: Project ID (optional)
            session_type: Type of session (default: 'comparison')
            metadata: Additional session metadata
        
        Returns:
            Created Session object
        """
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            project_id=project_id,
            session_type=session_type,
            status='active',
            session_metadata=metadata or {}
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Created session {session.id} (type: {session_type})")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.db.query(Session).filter(Session.id == session_id).first()
    
    def update_session_status(self, session_id: str, status: str, 
                             error_message: Optional[str] = None,
                             total_time: Optional[float] = None):
        """
        Update session status
        
        Args:
            session_id: Session ID
            status: New status
            error_message: Error message (if status is 'error')
            total_time: Total processing time in seconds
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.status = status
        session.updated_at = datetime.now(timezone.utc)
        
        if error_message:
            if not session.session_metadata:
                session.session_metadata = {}
            session.session_metadata['error_message'] = error_message
        
        if total_time is not None:
            session.total_time = total_time
        
        self.db.commit()
        logger.info(f"Updated session {session_id} status to {status}")
    
    def get_session_drawings(self, session_id: str, drawing_type: Optional[str] = None) -> List[Drawing]:
        """
        Get drawings for a session
        
        Args:
            session_id: Session ID
            drawing_type: Filter by type ('old' or 'new'), optional
        
        Returns:
            List of Drawing objects
        """
        query = self.db.query(Drawing).filter(Drawing.session_id == session_id)
        
        if drawing_type:
            query = query.filter(Drawing.drawing_type == drawing_type)
        
        return query.all()
    
    def get_session_comparisons(self, session_id: str) -> List[Comparison]:
        """Get all comparisons for a session"""
        return self.db.query(Comparison).filter(Comparison.session_id == session_id).all()
    
    def get_session_analyses(self, session_id: str) -> List[AnalysisResult]:
        """Get all analysis results for a session"""
        return self.db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).all()
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get aggregated summary for a session
        
        Returns:
            Dictionary with session summary data
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        comparisons = self.get_session_comparisons(session_id)
        analyses = self.get_session_analyses(session_id)
        
        # Calculate statistics
        total_pages = len(comparisons)
        successful_analyses = len([a for a in analyses if a.success])
        failed_analyses = len(analyses) - successful_analyses
        
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
                if isinstance(analysis.changes_found, list):
                    all_changes.extend(analysis.changes_found)
                else:
                    all_changes.append(analysis.changes_found)
            
            if analysis.recommendations:
                if isinstance(analysis.recommendations, list):
                    all_recommendations.extend(analysis.recommendations)
                else:
                    all_recommendations.append(analysis.recommendations)
        
        # Generate overall summary
        overall_summary = self._generate_overall_summary(analyses)
        
        return {
            'session_id': session_id,
            'session_status': session.status,
            'total_pages': total_pages,
            'total_analyses': len(analyses),
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
        }
    
    def _generate_overall_summary(self, analyses: List[AnalysisResult]) -> str:
        """Generate overall summary from analyses"""
        if not analyses:
            return "No analysis results available."
        
        successful_analyses = [a for a in analyses if a.success]
        if not successful_analyses:
            return "No successful analyses to summarize."
        
        # Count pages with critical changes
        critical_pages = len([a for a in successful_analyses if a.critical_change])
        total_pages = len(successful_analyses)
        
        summary_parts = []
        
        if critical_pages > 0:
            summary_parts.append(f"{critical_pages} of {total_pages} pages have critical changes requiring attention.")
        else:
            summary_parts.append(f"Analyzed {total_pages} pages - no critical issues identified.")
        
        # Add high-level insights
        if len(successful_analyses) > 0:
            summary_parts.append("Common themes include structural modifications, dimensional changes, and detail updates.")
        
        return " ".join(summary_parts)
    
    def get_recent_sessions(self, user_id: Optional[str] = None, limit: int = 20) -> List[Session]:
        """
        Get recent sessions
        
        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of sessions to return
        
        Returns:
            List of Session objects
        """
        query = self.db.query(Session)
        
        if user_id:
            query = query.filter(Session.user_id == user_id)
        
        return query.order_by(Session.created_at.desc()).limit(limit).all()
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all related data
        
        Args:
            session_id: Session ID
        
        Returns:
            True if deleted, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Cascade delete will handle related records
        self.db.delete(session)
        self.db.commit()
        
        logger.info(f"Deleted session {session_id}")
        return True
    
    def get_or_create_chat_conversation(self, session_id: str) -> ChatConversation:
        """
        Get or create a chat conversation for a session
        
        Args:
            session_id: Session ID
        
        Returns:
            ChatConversation object
        """
        conversation = self.db.query(ChatConversation).filter(
            ChatConversation.session_id == session_id
        ).first()
        
        if not conversation:
            conversation = ChatConversation(
                id=str(uuid.uuid4()),
                session_id=session_id
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            logger.info(f"Created chat conversation {conversation.id} for session {session_id}")
        
        return conversation

