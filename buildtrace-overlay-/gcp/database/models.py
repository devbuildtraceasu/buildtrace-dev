from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, ForeignKey, Boolean, Integer, Float, Index, UniqueConstraint, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

Base = declarative_base()

class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    company = Column(String(255))
    role = Column(String(100))  # architect, engineer, contractor, owner
    password_hash = Column(String(255))  # For email/password authentication
    last_login = Column(DateTime)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user")

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Required by Flask-Login"""
        return str(self.id)

    @property
    def is_authenticated(self):
        """Required by Flask-Login"""
        return True

    @property
    def is_anonymous(self):
        """Required by Flask-Login"""
        return False


class Project(Base):
    __tablename__ = 'projects'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    project_number = Column(String(100))  # External project ID if any
    client_name = Column(String(255))
    location = Column(String(255))
    status = Column(String(50), default='active')  # active, archived, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    sessions = relationship("Session", back_populates="project")
    drawing_versions = relationship("DrawingVersion", back_populates="project", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_user_project', 'user_id', 'name'),
    )


class DrawingVersion(Base):
    """Tracks different versions of the same drawing within a project"""
    __tablename__ = 'drawing_versions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    drawing_name = Column(String(100), nullable=False)  # e.g., A-101, S-12A
    version_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    version_label = Column(String(50))  # Optional: "Rev A", "IFC", "100% DD"
    upload_date = Column(DateTime, default=datetime.utcnow)
    drawing_id = Column(String(36), ForeignKey('drawings.id'), nullable=False)
    comments = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="drawing_versions")
    drawing = relationship("Drawing")

    # Indexes
    __table_args__ = (
        Index('idx_project_drawing_version', 'project_id', 'drawing_name', 'version_number', unique=True),
    )


class Session(Base):
    __tablename__ = 'sessions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)  # Nullable for anonymous sessions
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=True)  # Can be assigned later
    session_type = Column(String(50), default='comparison')  # comparison, upload, analysis
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default='active')  # active, processing, completed, error
    total_time = Column(Float)  # Processing time in seconds
    session_metadata = Column(JSON)  # Store session-specific metadata

    # Relationships
    user = relationship("User", back_populates="sessions")
    project = relationship("Project", back_populates="sessions")
    drawings = relationship("Drawing", back_populates="session", cascade="all, delete-orphan")
    comparisons = relationship("Comparison", back_populates="session", cascade="all, delete-orphan")
    chat_conversations = relationship("ChatConversation", back_populates="session", cascade="all, delete-orphan")


class Drawing(Base):
    __tablename__ = 'drawings'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    drawing_type = Column(String(20), nullable=False)  # 'old' or 'new'
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(Text)  # GCS path
    drawing_name = Column(String(100))  # Extracted drawing identifier (e.g., A-101)
    page_number = Column(Integer)
    processed_at = Column(DateTime, default=datetime.utcnow)
    drawing_metadata = Column(JSON)  # Store additional metadata like dimensions, scale, etc.

    # Relationships
    session = relationship("Session", back_populates="drawings")

    # Indexes
    __table_args__ = (
        Index('idx_session_drawing', 'session_id', 'drawing_name'),
        UniqueConstraint('session_id', 'drawing_name', 'drawing_type', name='unique_session_drawing_type'),
    )


class Comparison(Base):
    __tablename__ = 'comparisons'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    old_drawing_id = Column(String(36), ForeignKey('drawings.id'), nullable=False)
    new_drawing_id = Column(String(36), ForeignKey('drawings.id'), nullable=False)
    drawing_name = Column(String(100), nullable=False)
    overlay_path = Column(Text)  # GCS path to overlay image
    old_image_path = Column(Text)  # GCS path to processed old image
    new_image_path = Column(Text)  # GCS path to processed new image
    alignment_score = Column(Float)  # Quality of alignment (0-1)
    changes_detected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="comparisons")
    old_drawing = relationship("Drawing", foreign_keys=[old_drawing_id])
    new_drawing = relationship("Drawing", foreign_keys=[new_drawing_id])
    analysis_results = relationship("AnalysisResult", back_populates="comparison", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('session_id', 'drawing_name', name='unique_session_comparison'),
    )


class AnalysisResult(Base):
    __tablename__ = 'analysis_results'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comparison_id = Column(String(36), ForeignKey('comparisons.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)  # Direct session reference
    drawing_name = Column(String(100), nullable=False)
    changes_found = Column(JSON)  # List of changes
    critical_change = Column(Text)
    analysis_summary = Column(Text)
    recommendations = Column(JSON)  # List of recommendations
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    ai_model_used = Column(String(50), default='gpt-4-vision-preview')
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    comparison = relationship("Comparison", back_populates="analysis_results")

    # Constraints
    __table_args__ = (
        UniqueConstraint('session_id', 'drawing_name', name='unique_session_analysis'),
    )


class ChatConversation(Base):
    __tablename__ = 'chat_conversations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(JSON)  # Store additional metadata like token usage, model version

    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")


class ProcessingJob(Base):
    __tablename__ = 'processing_jobs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    job_type = Column(String(50), nullable=False)  # 'pdf_extraction', 'comparison', 'ai_analysis'
    status = Column(String(20), default='pending')  # pending, running, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    job_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


# Project-Users Association Table for many-to-many relationship
project_users = Table(
    'project_users',
    Base.metadata,
    Column('id', String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column('project_id', String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('role', String(50), default='member'),  # owner, admin, member, viewer
    Column('invited_at', DateTime, default=datetime.utcnow),
    Column('joined_at', DateTime),
    Column('invited_by', String(36), ForeignKey('users.id')),
    Column('user_name', String(255)),  # Denormalized for performance
    Column('user_email', String(255)),  # Denormalized for performance
    UniqueConstraint('project_id', 'user_id', name='uq_project_user')
)


# OAuth Token Storage
class OAuth(OAuthConsumerMixin, Base):
    __tablename__ = 'oauth'

    provider_user_id = Column(String(256), unique=True, nullable=False)
    user_id = Column(String(36), ForeignKey(User.id), nullable=False)
    user = relationship("User")


# Add indexes for performance
Index('idx_project_users_project_id', project_users.c.project_id)
Index('idx_project_users_user_id', project_users.c.user_id)
Index('idx_project_users_role', project_users.c.role)