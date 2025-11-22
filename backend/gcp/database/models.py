from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, ForeignKey, Boolean, Integer, BigInteger, Float, Index, UniqueConstraint, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Optional imports for authentication (only needed if using Flask-Login)
try:
    from flask_login import UserMixin
except ImportError:
    # Create a dummy UserMixin if flask_login is not available
    class UserMixin:
        pass

try:
    from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
except ImportError:
    # Create a dummy OAuthConsumerMixin if flask_dance is not available
    class OAuthConsumerMixin:
        pass

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
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=True)  # New: org support

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user")
    organization = relationship("Organization", back_populates="users")
    jobs = relationship("Job", back_populates="created_by_user", foreign_keys="Job.created_by")
    manual_overlays = relationship("ManualOverlay", back_populates="created_by_user")
    change_summaries = relationship("ChangeSummary", back_populates="created_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")

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


class Organization(Base):
    """Multi-tenant organization support"""
    __tablename__ = 'organizations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    domain = Column(String(255))  # For domain-based auth
    plan = Column(String(50), default='free')  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")

    # Indexes
    __table_args__ = (
        Index('idx_organizations_domain', 'domain'),
    )


class Project(Base):
    __tablename__ = 'projects'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(String(36), ForeignKey('organizations.id'), nullable=True)  # New: org support
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
    organization = relationship("Organization", back_populates="projects")
    sessions = relationship("Session", back_populates="project")
    drawing_versions = relationship("DrawingVersion", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")

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
    
    # Enhanced fields for OCR and processing
    ocr_status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    ocr_result_ref = Column(Text)  # GCS path to OCR JSON
    ocr_completed_at = Column(DateTime)
    rasterized_image_ref = Column(Text)  # GCS path to PNG
    file_hash = Column(String(64))  # SHA-256 for deduplication
    file_size = Column(BigInteger)  # Bytes

    # Relationships
    project = relationship("Project", back_populates="drawing_versions")
    drawing = relationship("Drawing")
    job_stages = relationship("JobStage", back_populates="drawing_version")
    diff_results_old = relationship("DiffResult", foreign_keys="DiffResult.old_drawing_version_id", back_populates="old_drawing_version")
    diff_results_new = relationship("DiffResult", foreign_keys="DiffResult.new_drawing_version_id", back_populates="new_drawing_version")

    # Indexes
    __table_args__ = (
        Index('idx_project_drawing_version', 'project_id', 'drawing_name', 'version_number', unique=True),
        Index('idx_drawing_versions_ocr_status', 'ocr_status'),
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
    drawing_versions = relationship("DrawingVersion", back_populates="drawing")

    # Indexes
    __table_args__ = (
        Index('idx_session_drawing', 'session_id', 'drawing_name'),
        UniqueConstraint('session_id', 'drawing_name', 'drawing_type', name='unique_session_drawing_type'),
    )


class Comparison(Base):
    """Legacy comparison table - kept for backward compatibility"""
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
    """Legacy analysis result table - kept for backward compatibility"""
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
    """Legacy processing job table - kept for backward compatibility"""
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


# ============================================================================
# NEW MODELS FOR ASYNC ARCHITECTURE
# ============================================================================

class Job(Base):
    """Job table for async processing workflow"""
    __tablename__ = 'jobs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    old_drawing_version_id = Column(String(36), ForeignKey('drawing_versions.id'), nullable=False)
    new_drawing_version_id = Column(String(36), ForeignKey('drawing_versions.id'), nullable=False)
    status = Column(String(50), default='created')  # created, in_progress, completed, failed, cancelled
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    cancelled_by = Column(String(36), ForeignKey('users.id'), nullable=True)
    error_message = Column(Text)
    job_metadata = Column(JSON)  # Store additional context

    # Relationships
    project = relationship("Project", back_populates="jobs")
    old_drawing_version = relationship("DrawingVersion", foreign_keys=[old_drawing_version_id])
    new_drawing_version = relationship("DrawingVersion", foreign_keys=[new_drawing_version_id])
    created_by_user = relationship("User", foreign_keys=[created_by], back_populates="jobs")
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by])
    job_stages = relationship("JobStage", back_populates="job", cascade="all, delete-orphan")
    diff_result = relationship("DiffResult", back_populates="job", uselist=False)

    # Indexes
    __table_args__ = (
        Index('idx_jobs_project', 'project_id'),
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_created_by', 'created_by'),
    )


class JobStage(Base):
    """Tracks individual stages (OCR, diff, summary) within a job"""
    __tablename__ = 'job_stages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    stage = Column(String(50), nullable=False)  # ocr, diff, summary
    drawing_version_id = Column(String(36), ForeignKey('drawing_versions.id'), nullable=True)  # For OCR stage
    status = Column(String(50), default='pending')  # pending, in_progress, completed, failed, skipped
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    result_ref = Column(Text)  # GCS path to stage output
    retry_count = Column(Integer, default=0)
    stage_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="job_stages")
    drawing_version = relationship("DrawingVersion", back_populates="job_stages")

    # Indexes
    __table_args__ = (
        Index('idx_job_stages_job', 'job_id'),
        Index('idx_job_stages_status', 'status'),
        Index('idx_job_stages_stage', 'stage'),
        UniqueConstraint('job_id', 'stage', 'drawing_version_id', name='uq_job_stage_drawing'),
    )


class DiffResult(Base):
    """Stores diff calculation results separately from comparisons"""
    __tablename__ = 'diff_results'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    old_drawing_version_id = Column(String(36), ForeignKey('drawing_versions.id'), nullable=False)
    new_drawing_version_id = Column(String(36), ForeignKey('drawing_versions.id'), nullable=False)
    machine_generated_overlay_ref = Column(Text, nullable=False)  # GCS path to diff JSON
    alignment_score = Column(Float)  # 0-1, quality of alignment
    changes_detected = Column(Boolean, default=False)
    change_count = Column(Integer, default=0)  # Total number of changes
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(36), ForeignKey('users.id'), nullable=True)  # System for machine-generated
    diff_metadata = Column(JSON)  # Store diff statistics, processing time, etc. (renamed from 'metadata')

    # Relationships
    job = relationship("Job", back_populates="diff_result")
    old_drawing_version = relationship("DrawingVersion", foreign_keys=[old_drawing_version_id], back_populates="diff_results_old")
    new_drawing_version = relationship("DrawingVersion", foreign_keys=[new_drawing_version_id], back_populates="diff_results_new")
    manual_overlays = relationship("ManualOverlay", back_populates="diff_result", cascade="all, delete-orphan")
    change_summaries = relationship("ChangeSummary", back_populates="diff_result", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_diff_results_job', 'job_id'),
        Index('idx_diff_results_versions', 'old_drawing_version_id', 'new_drawing_version_id'),
    )


class ManualOverlay(Base):
    """Stores human-corrected overlays, supports overlay versioning"""
    __tablename__ = 'manual_overlays'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    diff_result_id = Column(String(36), ForeignKey('diff_results.id', ondelete='CASCADE'), nullable=False)
    overlay_ref = Column(Text, nullable=False)  # GCS path to manual overlay JSON
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    is_active = Column(Boolean, default=True)  # Only one active overlay per diff
    parent_overlay_id = Column(String(36), ForeignKey('manual_overlays.id'), nullable=True)  # For overlay versioning
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    overlay_metadata = Column(JSON)  # Store edit history, change log (renamed from 'metadata')

    # Relationships
    diff_result = relationship("DiffResult", back_populates="manual_overlays")
    created_by_user = relationship("User", back_populates="manual_overlays")
    parent_overlay = relationship("ManualOverlay", remote_side=[id])
    child_overlays = relationship("ManualOverlay", back_populates="parent_overlay")
    change_summaries = relationship("ChangeSummary", back_populates="overlay")

    # Indexes
    __table_args__ = (
        Index('idx_manual_overlays_diff', 'diff_result_id'),
        Index('idx_manual_overlays_active', 'diff_result_id', 'is_active'),
        Index('idx_manual_overlays_created_by', 'created_by'),
    )


class ChangeSummary(Base):
    """Stores summaries with versioning, tracks machine vs human-generated"""
    __tablename__ = 'change_summaries'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    diff_result_id = Column(String(36), ForeignKey('diff_results.id', ondelete='CASCADE'), nullable=False)
    overlay_id = Column(String(36), ForeignKey('manual_overlays.id'), nullable=True)  # NULL for machine-generated, set for manual
    summary_text = Column(Text, nullable=False)
    summary_json = Column(JSON)  # Structured summary (bullet points, risk levels, etc.)
    source = Column(String(50), nullable=False)  # 'machine', 'human_corrected', 'human_written'
    ai_model_used = Column(String(50))  # 'gpt-4', 'gpt-4-vision', etc.
    created_by = Column(String(36), ForeignKey('users.id'), nullable=True)  # NULL for machine, set for human
    is_active = Column(Boolean, default=True)  # Only one active summary per diff
    parent_summary_id = Column(String(36), ForeignKey('change_summaries.id'), nullable=True)  # For summary versioning
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    summary_metadata = Column(JSON)  # Store prompt used, token usage, generation time, etc. (renamed from 'metadata')

    # Relationships
    diff_result = relationship("DiffResult", back_populates="change_summaries")
    overlay = relationship("ManualOverlay", back_populates="change_summaries")
    created_by_user = relationship("User", back_populates="change_summaries")
    parent_summary = relationship("ChangeSummary", remote_side=[id])
    child_summaries = relationship("ChangeSummary", back_populates="parent_summary")

    # Indexes
    __table_args__ = (
        Index('idx_change_summaries_diff', 'diff_result_id'),
        Index('idx_change_summaries_active', 'diff_result_id', 'is_active'),
        Index('idx_change_summaries_source', 'source'),
    )


class AuditLog(Base):
    """Tracks all user actions for compliance and debugging"""
    __tablename__ = 'audit_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    entity_type = Column(String(50), nullable=False)  # 'overlay', 'summary', 'project', etc.
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False)  # 'create', 'update', 'delete', 'view'
    changes = Column(JSON)  # Store before/after for updates
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user', 'user_id'),
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_logs_created', 'created_at'),
    )


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


# OAuth Token Storage (only if flask_dance is available)
try:
    from flask_dance.consumer.storage.sqla import OAuthConsumerMixin as _OAuthConsumerMixin
    
    class OAuth(_OAuthConsumerMixin, Base):
        __tablename__ = 'oauth'

        provider_user_id = Column(String(256), unique=True, nullable=False)
        user_id = Column(String(36), ForeignKey(User.id), nullable=False)
        user = relationship("User")
except ImportError:
    # OAuth model not available if flask_dance is not installed
    OAuth = None


# Add indexes for performance
Index('idx_project_users_project_id', project_users.c.project_id)
Index('idx_project_users_user_id', project_users.c.user_id)
Index('idx_project_users_role', project_users.c.role)

