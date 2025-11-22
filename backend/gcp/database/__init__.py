"""
Database module for BuildTrace GCP integration

Contains:
- database.py: PostgreSQL connection management and Cloud SQL configuration
- models.py: SQLAlchemy models for all database tables
- migrations/: Database schema migrations
"""

from .database import DatabaseManager, get_db, init_db, get_db_session
from .models import (
    Base, User, Project, DrawingVersion, Session, Drawing,
    Comparison, AnalysisResult, ChatConversation, ChatMessage, ProcessingJob,
    # New models for async architecture
    Organization, Job, JobStage, DiffResult, ManualOverlay, ChangeSummary, AuditLog
)

__all__ = [
    'DatabaseManager', 'get_db', 'init_db', 'get_db_session',
    'Base', 'User', 'Project', 'DrawingVersion', 'Session', 'Drawing',
    'Comparison', 'AnalysisResult', 'ChatConversation', 'ChatMessage', 'ProcessingJob',
    'Organization', 'Job', 'JobStage', 'DiffResult', 'ManualOverlay', 'ChangeSummary', 'AuditLog'
]

