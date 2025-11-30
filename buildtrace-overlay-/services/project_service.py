from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from models import User, Project, Session, DrawingVersion, Drawing, Comparison

class ProjectService:
    """Service layer for managing projects and drawing versions"""

    def __init__(self, db: DBSession):
        self.db = db

    def get_or_create_user(self, email: Optional[str] = None) -> User:
        """Get existing user or create anonymous/new user"""
        if not email:
            # Create anonymous user for now
            email = f"anonymous_{datetime.utcnow().timestamp()}@temp.com"
            user = User(email=email, name="Anonymous User")
            self.db.add(user)
            self.db.commit()
            return user

        # Check if user exists
        user = self.db.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email)
            self.db.add(user)
            self.db.commit()
        return user

    def get_or_create_default_project(self, user_id: str) -> Project:
        """Get user's default project or create one"""
        # Check for existing default project
        default_project = self.db.query(Project).filter_by(
            user_id=user_id,
            name="Default Project"
        ).first()

        if not default_project:
            default_project = Project(
                user_id=user_id,
                name="Default Project",
                description="Automatically created default project for organizing drawings"
            )
            self.db.add(default_project)
            self.db.commit()

        return default_project

    def create_project(self, user_id: str, name: str, **kwargs) -> Project:
        """Create a new project"""
        project = Project(
            user_id=user_id,
            name=name,
            description=kwargs.get('description'),
            project_number=kwargs.get('project_number'),
            client_name=kwargs.get('client_name'),
            location=kwargs.get('location')
        )
        self.db.add(project)
        self.db.commit()
        return project

    def move_session_to_project(self, session_id: str, project_id: str) -> bool:
        """Move a session (and its comparisons) to a specific project"""
        session = self.db.query(Session).filter_by(id=session_id).first()
        if session:
            session.project_id = project_id
            self.db.commit()
            return True
        return False

    def add_drawing_version(self, project_id: str, drawing: Drawing,
                           version_label: Optional[str] = None) -> DrawingVersion:
        """Add a drawing as a new version in a project"""
        # Get the latest version number for this drawing
        latest_version = self.db.query(DrawingVersion).filter_by(
            project_id=project_id,
            drawing_name=drawing.drawing_name
        ).order_by(DrawingVersion.version_number.desc()).first()

        version_number = 1 if not latest_version else latest_version.version_number + 1

        drawing_version = DrawingVersion(
            project_id=project_id,
            drawing_name=drawing.drawing_name,
            version_number=version_number,
            version_label=version_label,
            drawing_id=drawing.id
        )
        self.db.add(drawing_version)
        self.db.commit()
        return drawing_version

    def get_previous_version(self, project_id: str, drawing_name: str,
                            current_version: int) -> Optional[DrawingVersion]:
        """Get the previous version of a specific drawing"""
        return self.db.query(DrawingVersion).filter_by(
            project_id=project_id,
            drawing_name=drawing_name
        ).filter(
            DrawingVersion.version_number < current_version
        ).order_by(
            DrawingVersion.version_number.desc()
        ).first()

    def get_latest_drawing_versions(self, project_id: str) -> Dict[str, DrawingVersion]:
        """Get the latest version of each drawing in a project"""
        # Subquery to get max version for each drawing
        from sqlalchemy import func
        subq = self.db.query(
            DrawingVersion.drawing_name,
            func.max(DrawingVersion.version_number).label('max_version')
        ).filter_by(
            project_id=project_id
        ).group_by(
            DrawingVersion.drawing_name
        ).subquery()

        # Get the actual drawing versions
        latest_versions = self.db.query(DrawingVersion).join(
            subq,
            (DrawingVersion.drawing_name == subq.c.drawing_name) &
            (DrawingVersion.version_number == subq.c.max_version)
        ).filter_by(project_id=project_id).all()

        return {dv.drawing_name: dv for dv in latest_versions}

    def find_and_compare_with_previous(self, session_id: str, project_id: str):
        """
        For a new upload session, find previous versions of the same drawings
        and set up comparisons
        """
        # Get all new drawings from this session
        new_drawings = self.db.query(Drawing).filter_by(
            session_id=session_id,
            drawing_type='new'
        ).all()

        # Get latest versions of all drawings in the project
        latest_versions = self.get_latest_drawing_versions(project_id)

        comparisons_to_make = []
        for new_drawing in new_drawings:
            if new_drawing.drawing_name in latest_versions:
                # Found a previous version
                previous_version = latest_versions[new_drawing.drawing_name]
                comparisons_to_make.append({
                    'new_drawing': new_drawing,
                    'old_drawing_id': previous_version.drawing_id,
                    'drawing_name': new_drawing.drawing_name
                })

        return comparisons_to_make

    def list_user_projects(self, user_id: str) -> List[Project]:
        """List all projects for a user"""
        return self.db.query(Project).filter_by(
            user_id=user_id
        ).order_by(Project.updated_at.desc()).all()

    def get_project_statistics(self, project_id: str) -> Dict:
        """Get statistics about a project"""
        project = self.db.query(Project).filter_by(id=project_id).first()
        if not project:
            return {}

        # Count various metrics
        total_sessions = self.db.query(Session).filter_by(project_id=project_id).count()
        total_drawings = self.db.query(Drawing).join(Session).filter(
            Session.project_id == project_id
        ).count()
        total_comparisons = self.db.query(Comparison).join(Session).filter(
            Session.project_id == project_id
        ).count()

        # Get unique drawing names
        unique_drawings = self.db.query(DrawingVersion.drawing_name).filter_by(
            project_id=project_id
        ).distinct().count()

        return {
            'project_name': project.name,
            'created_at': project.created_at,
            'total_sessions': total_sessions,
            'total_drawings': total_drawings,
            'total_comparisons': total_comparisons,
            'unique_drawings': unique_drawings
        }