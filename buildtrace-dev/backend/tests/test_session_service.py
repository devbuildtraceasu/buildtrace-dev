#!/usr/bin/env python3
"""
Unit tests for SessionService

Tests session management, CRUD operations, and summary generation.
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession

from services.session_service import SessionService
from gcp.database.models import Session, Drawing, Comparison, AnalysisResult


class TestSessionService:
    """Test suite for SessionService"""
    
    @pytest.fixture
    def db_session(self, db):
        """Get database session"""
        return db
    
    @pytest.fixture
    def session_service(self, db_session):
        """Create SessionService instance"""
        return SessionService(db_session)
    
    @pytest.fixture
    def sample_session(self, session_service):
        """Create a sample session for testing"""
        return session_service.create_session(
            user_id=str(uuid.uuid4()),
            session_type='comparison',
            metadata={'test': True}
        )
    
    def test_create_session(self, session_service):
        """Test session creation"""
        session = session_service.create_session(
            user_id=str(uuid.uuid4()),
            session_type='comparison'
        )
        
        assert session is not None
        assert session.id is not None
        assert session.status == 'active'
        assert session.session_type == 'comparison'
    
    def test_get_session(self, session_service, sample_session):
        """Test getting a session by ID"""
        retrieved = session_service.get_session(sample_session.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_session.id
        assert retrieved.status == 'active'
    
    def test_update_session_status(self, session_service, sample_session):
        """Test updating session status"""
        session_service.update_session_status(
            sample_session.id,
            'processing',
            total_time=10.5
        )
        
        updated = session_service.get_session(sample_session.id)
        assert updated.status == 'processing'
        assert updated.total_time == 10.5
    
    def test_get_session_summary(self, session_service, sample_session, db_session):
        """Test getting session summary"""
        # Create sample comparison
        comparison = Comparison(
            id=str(uuid.uuid4()),
            session_id=sample_session.id,
            old_drawing_id=str(uuid.uuid4()),
            new_drawing_id=str(uuid.uuid4()),
            drawing_name='A-101',
            changes_detected=True,
            alignment_score=0.95
        )
        db_session.add(comparison)
        
        # Create sample analysis
        analysis = AnalysisResult(
            id=str(uuid.uuid4()),
            comparison_id=comparison.id,
            session_id=sample_session.id,
            drawing_name='A-101',
            changes_found=['Change 1', 'Change 2'],
            critical_change='Critical change detected',
            recommendations=['Recommendation 1'],
            success=True
        )
        db_session.add(analysis)
        db_session.commit()
        
        summary = session_service.get_session_summary(sample_session.id)
        
        assert summary is not None
        assert summary['session_id'] == sample_session.id
        assert summary['total_pages'] == 1
        assert summary['total_analyses'] == 1
        assert summary['successful_analyses'] == 1
        assert summary['critical_changes_count'] == 1
    
    def test_get_recent_sessions(self, session_service):
        """Test getting recent sessions"""
        # Create multiple sessions
        for i in range(5):
            session_service.create_session(
                user_id=str(uuid.uuid4()),
                session_type='comparison'
            )
        
        recent = session_service.get_recent_sessions(limit=3)
        assert len(recent) == 3
    
    def test_delete_session(self, session_service, sample_session):
        """Test deleting a session"""
        deleted = session_service.delete_session(sample_session.id)
        
        assert deleted is True
        
        # Verify session is deleted
        retrieved = session_service.get_session(sample_session.id)
        assert retrieved is None
    
    def test_get_or_create_chat_conversation(self, session_service, sample_session):
        """Test getting or creating chat conversation"""
        conversation = session_service.get_or_create_chat_conversation(sample_session.id)
        
        assert conversation is not None
        assert conversation.session_id == sample_session.id
        
        # Get again should return same conversation
        conversation2 = session_service.get_or_create_chat_conversation(sample_session.id)
        assert conversation2.id == conversation.id

